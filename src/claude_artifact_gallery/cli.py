"""Scan a folder tree for Claude artifacts and build one gallery page.

Usage: claude-artifact-gallery [ROOT] [-o OUT] [--no-open] [--version]
       claude-artifact-gallery add HTML --url URL_OR_ID [--title TITLE] [--group GROUP]
       claude-artifact-gallery install-skill [--all] [--profile CONFIG_DIR]... [--dir SKILLS_DIR]... [--force]
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

from . import skill
from .cache import cache_dir
from .model import Item, merge
from .page import render
from .sources.archify import find_archify
from .sources.canvas import find_canvases
from .sources.pulled import add_pulled, artifact_url, canvas_folder, find_pulled
from .sources.registry import find_registries, parse_registry


def _warn(msg: str) -> None:
    print(msg, file=sys.stderr)


def _ok(headline: str, *details: str) -> None:
    """A check-marked result line, then one indented line per detail."""
    print(f"✓ {headline}")
    for d in details:
        print(f"  {d}")


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
            saved = pulled.pop(i.url)
            items[n] = replace(i, href=saved.href, boards=saved.boards, notes=saved.notes, date=i.date or saved.date)
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
                                 description="Save a claude.ai artifact (its HTML file, or a design canvas folder) so the gallery can embed it.")
    ap.add_argument("html", metavar="HTML_OR_CANVAS_DIR",
                    help="local file holding the artifact's HTML, or the folder with its canvas.json (or the folder above `project/`)")
    ap.add_argument("--url", required=True, help="the artifact's claude.ai link, or just its id")
    ap.add_argument("--title", help="default: the HTML <title> or the canvas title, else the file name")
    ap.add_argument("--group", default="pulled")
    args = ap.parse_args(argv)
    try:
        url = artifact_url(args.url)
        html = Path(args.html)
        if html.is_dir():
            folder = canvas_folder(html)
            if not folder:
                raise ValueError(f"{html} has no canvas.json (looked in it and in project/)")
            title_source = json.loads((folder / "canvas.json").read_text(encoding="utf-8")).get("title") or ""
        else:
            text = html.read_text(encoding="utf-8", errors="replace")
            found = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
            title_source = found.group(1).strip() if found else ""
    except ValueError as e:
        _warn(str(e))
        return 1
    except OSError as e:
        _warn(f"cannot read {args.html}: {e.strerror}\n"
              "  `add` saves an HTML file you already have. To fetch a private claude.ai artifact from its link or id,\n"
              "  run /artifact-gallery-pull <link-or-id> inside Claude Code (install it once with: claude-artifact-gallery install-skill).")
        return 1
    title = args.title or title_source or html.stem
    dest = add_pulled(html, url, title, args.group)
    _ok(f"Saved \"{title}\"", url, f"{dest}")
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
                            description="Install the latest version from GitHub and refresh the /artifact-gallery-pull skill.").parse_args(argv)
    method, detail = install_method()
    if method == "local":
        print(f"This copy runs from a local folder, so there is nothing to download.\n  {detail}\n"
              "  Update it there: git pull, then pip install -e . again if needed.")
        return 0
    if method == "unknown":
        _warn(f"Cannot tell how this was installed. Update by hand with:\n  {MANUAL_UPGRADE}")
        return 1
    cmd = (["pipx", "install", "--force", REPO_URL] if method == "pipx"
           else [sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", REPO_URL])
    print(f"Upgrading with {method}...\n  {' '.join(cmd)}")
    try:
        code = subprocess.run(cmd).returncode
    except OSError as e:
        _warn(f"cannot run {cmd[0]}: {e.strerror}\nUpdate by hand with:\n  {MANUAL_UPGRADE}")
        return 1
    if code:
        _warn(f"upgrade failed (exit {code}); git and network access are needed. By hand:\n  {MANUAL_UPGRADE}")
        return code
    have = [p for p in skill.profiles() if skill.is_installed(p / "skills")]
    if have:  # the new code is on disk, so refresh the skill with it, not with this old process
        flags = [f for p in have for f in ("--profile", str(p))]
        subprocess.run([sys.executable, "-m", "claude_artifact_gallery.cli", "install-skill", "--force", *flags])
    _ok("Upgraded to " + subprocess.run([sys.executable, "-m", "claude_artifact_gallery.cli", "--version"],
                                        capture_output=True, text=True).stdout.strip())
    return 0


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
    """A hint naming the profiles whose installed skill is out of date, else ''."""
    stale = skill.outdated_profiles()
    if not stale:
        return ""
    flags = " ".join(f"--profile {p}" for p in stale)
    return (f"the /{skill.NAME} skill is out of date in {', '.join(str(p) for p in stale)}: "
            f"run claude-artifact-gallery install-skill --force {flags}")


def install_skill(argv) -> int:
    ap = argparse.ArgumentParser(prog="claude-artifact-gallery install-skill",
                                 description=f"Install the /{skill.NAME} skill into Claude Code so it works in every project.")
    ap.add_argument("--all", action="store_true", help="every Claude profile found (~/.claude, ~/.claude-*, $CLAUDE_CONFIG_DIR)")
    ap.add_argument("--profile", action="append", default=[], metavar="CONFIG_DIR",
                    help="a Claude config folder, e.g. ~/.claude-work (repeatable)")
    ap.add_argument("--dir", action="append", default=[], metavar="SKILLS_DIR", help="a skills folder (repeatable)")
    ap.add_argument("--force", action="store_true", help="overwrite a different existing skill")
    args = ap.parse_args(argv)
    explicit = args.all or args.profile or args.dir
    targets = [p / "skills" for p in (skill.profiles() if args.all else [])]
    targets += [Path(p).expanduser() / "skills" for p in args.profile] + [Path(d).expanduser() for d in args.dir]
    if not targets:
        targets = [skill.current_profile() / "skills"]
    code, installed, seen = 0, False, set()
    for skills_dir in targets:
        if skills_dir.resolve() in seen:
            continue
        seen.add(skills_dir.resolve())
        status, dest, legacy = skill.install(skills_dir, args.force)
        if status == "conflict":
            _warn(f"{dest} exists and differs; use --force to overwrite it")
            code = 1
            continue
        installed = installed or status == "installed"
        _ok(f"/{skill.NAME} skill " + ("installed" if status == "installed" else "is already up to date"), f"{dest}",
            *([f"removed the old /{skill.LEGACY_NAME} skill: {legacy}"] if legacy else []))
    if installed:
        print("  Restart Claude Code (or open a new session) to use it.")
    others = [p for p in skill.profiles() if (p / "skills").resolve() not in seen]
    if others and not explicit:
        _warn("! Other Claude profiles found: " + ", ".join(str(p) for p in others)
              + "\n  Add --all, or --profile DIR, to install there too.")
    return code


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
    _ok(f"{len(items)} artifact{'' if len(items) == 1 else 's'}",
        " · ".join(f"{k} {counts[k]}" for k in ("archify", "registry", "canvas", "pulled", "skipped")), f"{out}")
    hint = stale_skill_hint()
    if hint:
        _warn(f"! {hint}")
    if not args.no_open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
