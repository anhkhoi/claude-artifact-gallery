"""Find design canvases: folders with a `canvas.json` and `*.dc.html` boards."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List

from ..model import Item
from . import SKIP_DIRS

GAP = 80  # vertical gap between boards that have no position of their own


def _board_title(name: str, spec: dict) -> str:
    return spec.get("title") or (name[:-len(".dc.html")] if name.endswith(".dc.html") else Path(name).stem)


def _dim(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _note(spec: dict) -> dict:
    return {"x": _dim(spec.get("x"), 0), "y": _dim(spec.get("y"), 0),
            "w": _dim(spec.get("w") or spec.get("maxW"), 0),
            "kind": str(spec.get("kind") or ""), "fill": str(spec.get("fill") or ""),
            "text": str(spec.get("text") or "")}


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
            boards, cursor = [], 0
            newest = (folder / "canvas.json").stat().st_mtime
            for name in order:
                f = folder / name
                if not f.is_file():
                    continue
                spec = specs.get(name) or {}
                newest = max(newest, f.stat().st_mtime)
                w, h = _dim(spec.get("w"), 1000), _dim(spec.get("h"), 800)
                placed = "x" in spec and "y" in spec
                x, y = (_dim(spec["x"], 0), _dim(spec["y"], 0)) if placed else (0, cursor)
                cursor = max(cursor, y + h + GAP)
                boards.append({"title": _board_title(name, spec), "href": f.resolve().as_uri(),
                               "x": x, "y": y, "w": w, "h": h})
            notes = [_note(n) for n in (cj.get("notes") or {}).values() if isinstance(n, dict)]
        except (OSError, ValueError, AttributeError, TypeError) as e:
            warn(f"{folder / 'canvas.json'}: skipped canvas ({e})")
            continue
        items.append(Item(kind="canvas", title=cj.get("title") or folder.name, group=folder.parent.name,
                          date=datetime.fromtimestamp(newest).strftime("%Y-%m-%d"),
                          boards=boards, notes=notes, meta={"dir": folder.resolve()}))
    return items
