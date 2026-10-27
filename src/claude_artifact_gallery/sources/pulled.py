"""HTML of claude.ai artifacts saved locally by `claude-artifact-gallery add`."""
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from ..cache import cache_dir
from ..model import Item


def pulled_dir() -> Path:
    path = cache_dir() / "pulled"
    path.mkdir(parents=True, exist_ok=True)
    return path


def add_pulled(html: Path, url: str, title: str, group: str = "pulled") -> Path:
    """Copy `html` into the pulled folder, keyed by `url`; adding the same url again refreshes it."""
    stem = hashlib.sha1(url.encode()).hexdigest()[:12]
    dest = pulled_dir() / f"{stem}.html"
    shutil.copyfile(html, dest)
    meta = {"url": url, "title": title, "group": group, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
    dest.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
    return dest


def find_pulled() -> List[Item]:
    items = []
    for sidecar in sorted(pulled_dir().glob("*.json")):
        html = sidecar.with_suffix(".html")
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
            size = html.stat().st_size
            items.append(Item(kind="pulled", title=meta["title"], group=meta.get("group") or "pulled",
                              date=meta.get("date", ""), url=meta["url"], href=html.resolve().as_uri(),
                              meta={"size": size}))
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
