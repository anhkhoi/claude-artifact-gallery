"""Find `.archify/<run>/*.html` outputs."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List

from ..model import Item
from . import SKIP_DIRS


def _load_json(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _archify_dirs(root: Path):
    for dirpath, dirnames, _ in os.walk(root):
        if ".archify" in dirnames:
            yield Path(dirpath) / ".archify"
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and d != ".archify")


def find_archify(root: Path) -> List[Item]:
    items = []
    for adir in _archify_dirs(root):
        project = adir.parent.relative_to(root).as_posix() or "."
        try:
            runs = sorted(p for p in adir.iterdir() if p.is_dir())
        except OSError:
            continue
        for run in runs:
            cand = _load_json(run / "candidate.json")
            meta = cand.get("meta") if isinstance(cand.get("meta"), dict) else {}
            for html in sorted(run.glob("*.html")):
                finalize = _load_json(html.with_suffix(".finalize-summary.json"))
                check = _load_json(html.with_suffix(".browser-check.json"))
                try:
                    st = html.stat()
                except OSError:
                    continue
                items.append(Item(
                    kind="archify", title=meta.get("title") or html.stem, group=project,
                    date=datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    href=html.resolve().as_uri(),
                    tags=[cand.get("diagram_type") or run.name.split("-")[0]],
                    meta={"size": st.st_size, "run": run.name,
                          "check": check.get("status") or ("ok" if finalize.get("ok") else "")}))
    return items
