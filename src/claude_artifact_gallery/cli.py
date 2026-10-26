"""Scan a folder tree for Claude artifacts and build one gallery page.

Usage: claude-artifact-gallery [ROOT] [-o OUT] [--no-open]
  ROOT  folder to scan recursively (default: git root of cwd, else cwd)
  OUT   gallery file (default: ~/.cache/claude-artifact-gallery/<root>-<hash>.html,
        so no file is written into your repo)

Sources: artifacts.md registries (claude.ai links) and design
canvases (canvas.json + *.dc.html). Re-run to refresh.
"""
import argparse
import hashlib
import os
import subprocess
import sys
import webbrowser
from collections import Counter
from pathlib import Path
from typing import List, Tuple

from .model import Item, merge
from .page import render
from .sources.canvas import find_canvases
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
    items.sort(key=lambda i: i.date, reverse=True)
    counts = Counter(i.kind for i in items)
    return items, {"registry": counts["registry"], "canvas": counts["canvas"], "skipped": skipped}


def default_root() -> Path:
    """Git top-level of the cwd, else the cwd itself."""
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                             text=True, check=True).stdout.strip()
        return Path(top)
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()


def default_out(root: Path) -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "claude-artifact-gallery"
    cache.mkdir(parents=True, exist_ok=True)
    return cache / f"{root.name}-{hashlib.sha1(str(root).encode()).hexdigest()[:8]}.html"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", help="folder to scan (default: git root of cwd, else cwd)")
    ap.add_argument("-o", "--out")
    ap.add_argument("--no-open", action="store_true", help="only write the file, do not open the browser")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else default_root()
    out = Path(args.out).resolve() if args.out else default_out(root)
    items, counts = collect(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(items), encoding="utf-8")
    print(f"{len(items)} artifact(s): registry {counts['registry']}, "
          f"canvas {counts['canvas']}, skipped {counts['skipped']} -> {out}")
    if not args.no_open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
