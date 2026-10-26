"""Find design canvases: folders with a `canvas.json` and `*.dc.html` boards."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List

from ..model import Item
from . import SKIP_DIRS


def _board_title(name: str, spec: dict) -> str:
    return spec.get("title") or (name[:-len(".dc.html")] if name.endswith(".dc.html") else Path(name).stem)


def _dim(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def find_canvases(root: Path, warn=print) -> List[Item]:
    items = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if "canvas.json" not in filenames:
            continue
        folder = Path(dirpath)
        try:
            cj = json.loads((folder / "canvas.json").read_text(encoding="utf-8"))
            specs = cj.get("boards") or {}
            order = cj.get("order") or list(specs)
            boards, newest = [], (folder / "canvas.json").stat().st_mtime
            for name in order:
                f = folder / name
                if not f.is_file():
                    continue
                spec = specs.get(name) or {}
                newest = max(newest, f.stat().st_mtime)
                boards.append({"title": _board_title(name, spec), "href": f.resolve().as_uri(),
                               "w": _dim(spec.get("w"), 1000), "h": _dim(spec.get("h"), 800)})
        except (OSError, ValueError, AttributeError, TypeError) as e:
            warn(f"{folder / 'canvas.json'}: skipped canvas ({e})")
            continue
        items.append(Item(kind="canvas", title=cj.get("title") or folder.name, group=folder.parent.name,
                          date=datetime.fromtimestamp(newest).strftime("%Y-%m-%d"),
                          boards=boards, meta={"dir": folder.resolve()}))
    return items
