"""Parse `artifacts.md` registries listing claude.ai artifacts."""
import os
import re
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

from ..model import Item
from . import SKIP_DIRS

BULLET = re.compile(r"^\s*[-*+]\s+\[")  # a list item that starts with a link
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
LINE = re.compile(r"^\s*[-*+]\s+\[(?P<title>.+?)\]\((?P<url>https?://\S+?)\):\s*(?P<rest>.*)$")
DATE = re.compile(r"\((\d{4}-\d{2}-\d{2})")
COPY = re.compile(r"Copy:\s*(\S.*)")
TICKED_RUN = re.compile(r"^((?:`[^`]+`(?:,\s*)?)+)")
TICKED = re.compile(r"`([^`]+)`")


def find_registries(root: Path) -> List[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if "artifacts.md" in filenames:
            found.append(Path(dirpath) / "artifacts.md")
    return found


def _copy_candidates(rest: str) -> List[str]:
    """Paths named after `Copy:`; backticked (one or more) or a single bare token."""
    m = COPY.search(rest)
    if not m:
        return []
    run = TICKED_RUN.match(m[1])
    if run:
        return TICKED.findall(run[1])
    return [m[1].split()[0].rstrip(".,;")]


def _bases(registry: Path, root: Path) -> Iterator[Path]:
    """Where relative Copy paths may start: ROOT, then the registry's folder and its parents up to the git root."""
    yield root
    for d in [registry.parent, *registry.parent.parents]:
        yield d
        if (d / ".git").exists():
            break


def parse_registry(path: Path, root: Path, warn=print) -> Tuple[List[Item], Dict[str, Path]]:
    """Items plus a map of registry url -> existing Copy folder."""
    items, copies = [], {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as e:
        warn(f"{path}: skipped registry ({e})")
        return items, copies
    group = ""
    for n, line in enumerate(lines, 1):
        h = HEADING.match(line)
        if h:
            group = h[1]
            continue
        if not BULLET.match(line):
            continue
        m = LINE.match(line)
        if not m:
            warn(f"{path}:{n}: skipped registry line, expected - [title](https://...): purpose")
            continue
        rest = m["rest"]
        d = DATE.search(rest)
        purpose = rest[:d.start()] if d else re.split(r"\s*Copy:", rest)[0]
        items.append(Item(kind="registry", title=m["title"], group=group,
                          purpose=purpose.strip(), date=d[1] if d else "", url=m["url"]))
        found = next((f for p in _copy_candidates(rest) for b in _bases(path, root)
                      for f in [(b / p).resolve()] if f.is_dir()), None)
        if found:
            copies[m["url"]] = found
    return items, copies
