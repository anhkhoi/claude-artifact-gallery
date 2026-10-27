"""HTML of claude.ai artifacts saved locally by `claude-artifact-gallery add`."""
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..cache import cache_dir
from ..model import Item
from .canvas import find_canvases


def pulled_dir() -> Path:
    path = cache_dir() / "pulled"
    path.mkdir(parents=True, exist_ok=True)
    return path


def canvas_folder(path: Path) -> Optional[Path]:
    """The folder holding `canvas.json` for `path` itself or its `project/` subfolder, else None."""
    for candidate in (path, path / "project"):
        if (candidate / "canvas.json").is_file():
            return candidate
    return None


def add_pulled(src: Path, url: str, title: str, group: str = "pulled") -> Path:
    """Copy an HTML file, or a canvas folder, into the pulled folder keyed by `url`; adding it again refreshes it."""
    stem = hashlib.sha1(url.encode()).hexdigest()[:12]
    folder = pulled_dir() / stem
    page = pulled_dir() / f"{stem}.html"
    for old in (folder, page):  # a url may change from page to canvas between pulls
        shutil.rmtree(old) if old.is_dir() else old.unlink() if old.exists() else None
    meta = {"url": url, "title": title, "group": group, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
    if src.is_dir():
        shutil.copytree(canvas_folder(src), folder, ignore=shutil.ignore_patterns("support.js"))
        meta["canvas"] = True
        dest = folder
    else:
        shutil.copyfile(src, page)
        dest = page
    (pulled_dir() / f"{stem}.json").write_text(json.dumps(meta), encoding="utf-8")
    return dest


def find_pulled() -> List[Item]:
    items = []
    for sidecar in sorted(pulled_dir().glob("*.json")):
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
            common = dict(kind="pulled", title=meta["title"], group=meta.get("group") or "pulled",
                          date=meta.get("date", ""), url=meta["url"])
            if meta.get("canvas"):
                canvas = next(iter(find_canvases(sidecar.with_suffix(""), lambda msg: None)), None)
                if canvas:
                    items.append(Item(**common, boards=canvas.boards, notes=canvas.notes, meta={"dir": canvas.meta["dir"]}))
                continue
            html = sidecar.with_suffix(".html")
            items.append(Item(**common, href=html.resolve().as_uri(), meta={"size": html.stat().st_size}))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return items


_ID = r"[0-9A-Za-z][0-9A-Za-z_-]*"


def artifact_url(ref: str) -> str:
    """A claude.ai artifact link from a link or a bare id; raises ValueError for anything else."""
    ref = ref.strip()
    if re.fullmatch(_ID, ref):
        return f"https://claude.ai/artifact/{ref}"
    found = re.fullmatch(rf"https?://claude\.ai/(?:code/)?artifact/({_ID})/?(?:[?#].*)?", ref)
    if not found:
        raise ValueError(f"not a claude.ai artifact link or id: {ref}")
    return ref.split("?")[0].split("#")[0].rstrip("/")
