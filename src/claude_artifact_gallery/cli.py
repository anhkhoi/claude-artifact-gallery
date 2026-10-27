"""Scan a folder tree for Claude artifacts and build one gallery page.

Usage: claude-artifact-gallery [ROOT] [-o OUT] [--no-open] [--version]
       claude-artifact-gallery add HTML --url URL_OR_ID [--title TITLE] [--group GROUP]
       claude-artifact-gallery install-skill [--dir SKILLS_DIR] [--force]
       claude-artifact-gallery upgrade
  ROOT  folder to scan recursively (default: git root of cwd, else cwd)
  OUT   gallery file (default: ~/.cache/claude-artifact-gallery/<root>-<hash>.html,
        so no file is written into your repo)

Sources: .archify/ outputs, artifacts.md registries (claude.ai links), and
design canvases (canvas.json + *.dc.html), and claude.ai artifacts saved with `add`
(Claude Code reads the private artifact; `add` stores its HTML so the gallery can embed it). Re-run to refresh.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from collections import Counter
from importlib import metadata
from dataclasses import replace
from pathlib import Path
from typing import List, Tuple

from .cache import cache_dir
from .model import Item, merge
from .page import render
from .sources.archify import find_archify
from .sources.canvas import find_canvases
from .sources.pulled import add_pulled, artifact_url, find_pulled
from .sources.registry import find_registries, parse_registry


def _warn(msg: str) -> None:
    print(msg, file=sys.stderr)


def collect(root: Path, warn=_warn) -> Tuple[List[Item], dict]:
    skipped = 0

    def counted(msg: str) -> None:
        nonlocal skipped
        skipped += 1
        warn(msg)

    registry, copies = [], {}
    for path in find_registries(root):
        items, found = parse_registry(path, root, counted)
        registry += items
        copies.update(found)
    items = merge(registry, find_canvases(root, counted), copies)
    pulled = {p.url: p for p in find_pulled()}
    for n, i in enumerate(items):  # a saved copy of a registry link is shown on that entry, not twice
        if i.url in pulled and not i.boards:
            items[n] = replace(i, href=pulled.pop(i.url).href)
    items += list(pulled.values()) + find_archify(root)
    items.sort(key=lambda i: i.date, reverse=True)
    counts = Counter(i.kind for i in items)
    return items, {"archify": counts["archify"], "registry": counts["registry"],
                   "canvas": counts["canvas"], "pulled": counts["pulled"], "skipped": skipped}


def default_root() -> Path:
    """Git top-level of the cwd, else the cwd itself."""
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                             text=True, check=True).stdout.strip()
        return Path(top)
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()


def default_out(root: Path) -> Path:
    return cache_dir() / f"{root.name}-{hashlib.sha1(str(root).encode()).hexdigest()[:8]}.html"


def add(argv) -> int:
    ap = argparse.ArgumentParser(prog="claude-artifact-gallery add",
                                 description="Save the HTML of a claude.ai artifact so the gallery can embed it.")
    ap.add_argument("html", help="local file holding the artifact's HTML")
    ap.add_argument("--url", required=True, help="the artifact's claude.ai link, or just its id")
    ap.add_argument("--title", help="default: the HTML <title>, else the file name")
    ap.add_argument("--group", default="pulled")
    args = ap.parse_args(argv)
    try:
        url = artifact_url(args.url)
        html = Path(args.html)
        text = html.read_text(encoding="utf-8", errors="replace")
    except ValueError as e:
        _warn(str(e))
        return 1
    except OSError as e:
        _warn(f"cannot read {args.html}: {e.strerror}")
        return 1
    found = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    title = args.title or (found and found.group(1).strip()) or html.stem
    dest = add_pulled(html, url, title, args.group)
    print(f"saved '{title}' ({url}) -> {dest}")
    return 0


REPO_URL = "git+https://github.com/anhkhoi/claude-artifact-gallery.git"
MANUAL_UPGRADE = f"pipx install --force {REPO_URL}"


def install_method() -> Tuple[str, str]:
    """How this copy was installed: ("pipx" | "pip" | "local" | "unknown", detail)."""
    try:
        dist = metadata.distribution("claude-artifact-gallery")
        direct = json.loads(dist.read_text("direct_url.json") or "{}")
    except (metadata.PackageNotFoundError, ValueError):
        return "unknown", ""
    if "dir_info" in direct:  # a local folder, editable or not
        return "local", direct.get("url", "")
    parts = Path(sys.prefix).parts
    if "pipx" in parts and "venvs" in parts:
        return "pipx", ""
    return "pip", ""


def upgrade(argv) -> int:
    argparse.ArgumentParser(prog="claude-artifact-gallery upgrade",
                            description="Install the latest version from GitHub and refresh the /pull skill.").parse_args(argv)
    method, detail = install_method()
    if method == "local":
        print(f"This copy runs from a local folder ({detail}).\nUpdate it there: git pull, then pip install -e . again if needed.")
        return 0
    if method == "unknown":
        _warn(f"Cannot tell how this was installed. Update by hand with:\n  {MANUAL_UPGRADE}")
        return 1
    cmd = (["pipx", "install", "--force", REPO_URL] if method == "pipx"
           else [sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", REPO_URL])
    print(f"Upgrading with {method}: {' '.join(cmd)}")
    try:
        code = subprocess.run(cmd).returncode
    except OSError as e:
        _warn(f"cannot run {cmd[0]}: {e.strerror}\nUpdate by hand with:\n  {MANUAL_UPGRADE}")
        return 1
    if code:
        _warn(f"upgrade failed (exit {code}); git and network access are needed. By hand:\n  {MANUAL_UPGRADE}")
        return code
    if skill_dest().exists():  # the new code is on disk, so refresh the skill with it, not with this old process
        subprocess.run([sys.executable, "-m", "claude_artifact_gallery.cli", "install-skill", "--force"])
    print("Upgraded: " + subprocess.run([sys.executable, "-m", "claude_artifact_gallery.cli", "--version"],
                                        capture_output=True, text=True).stdout.strip())
    return 0


SKILL_SRC = Path(__file__).parent / "skills" / "pull" / "SKILL.md"


def skill_dest(skills_dir=None) -> Path:
    config = os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    return (Path(skills_dir) if skills_dir else Path(config) / "skills") / "pull" / "SKILL.md"


def version_string() -> str:
    """`0.1.0 (commit abc1234)` for a git install, else just the version."""
    try:
        dist = metadata.distribution("claude-artifact-gallery")
        text = f"{dist.version}"
        direct = dist.read_text("direct_url.json")
        commit = (json.loads(direct).get("vcs_info") or {}).get("commit_id") if direct else None
        return f"{text} (commit {commit[:7]})" if commit else text
    except (metadata.PackageNotFoundError, ValueError, AttributeError):
        return "unknown"


def stale_skill_hint() -> str:
    """A hint when an installed /pull skill differs from the packaged one, else ''."""
    dest = skill_dest()
    try:
        if dest.exists() and dest.read_bytes() != SKILL_SRC.read_bytes():
            return f"the /pull skill at {dest} is out of date: run claude-artifact-gallery install-skill --force"
    except OSError:
        pass
    return ""


def install_skill(argv) -> int:
    ap = argparse.ArgumentParser(prog="claude-artifact-gallery install-skill",
                                 description="Install the /pull skill into Claude Code so it works in every project.")
    ap.add_argument("--dir", help="skills folder (default: $CLAUDE_CONFIG_DIR/skills, else ~/.claude/skills)")
    ap.add_argument("--force", action="store_true", help="overwrite a different existing skill")
    args = ap.parse_args(argv)
    dest, src = skill_dest(args.dir), SKILL_SRC
    if dest.exists() and dest.read_bytes() == src.read_bytes():
        print(f"/pull is already up to date: {dest}")
        return 0
    if dest.exists() and not args.force:
        _warn(f"{dest} exists and differs; use --force to overwrite it")
        return 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    print(f"installed /pull -> {dest}\nRestart Claude Code (or start a new session) to pick it up.")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] == "add":
        return add(argv[1:])
    if argv and argv[0] == "install-skill":
        return install_skill(argv[1:])
    if argv and argv[0] == "upgrade":
        return upgrade(argv[1:])
    ap = argparse.ArgumentParser(prog="claude-artifact-gallery", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", help="folder to scan (default: git root of cwd, else cwd)")
    ap.add_argument("-o", "--out")
    ap.add_argument("--no-open", action="store_true", help="only write the file, do not open the browser")
    ap.add_argument("--version", action="version", version=f"%(prog)s {version_string()}")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else default_root()
    out = Path(args.out).resolve() if args.out else default_out(root)
    items, counts = collect(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(items, root), encoding="utf-8")
    print(f"{len(items)} artifact(s): archify {counts['archify']}, registry {counts['registry']}, "
          f"canvas {counts['canvas']}, pulled {counts['pulled']}, skipped {counts['skipped']} -> {out}")
    hint = stale_skill_hint()
    if hint:
        _warn(hint)
    if not args.no_open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
