"""The single item type shared by all sources and the page."""
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, List


@dataclass
class Item:
    kind: str  # "registry" | "canvas"
    title: str
    group: str
    purpose: str = ""
    date: str = ""
    url: str = ""   # claude.ai URL, "" when none
    href: str = ""  # file:// URI of the page to embed, "" when none
    boards: list = field(default_factory=list)  # [{"title", "href", "w", "h"}]
    tags: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["meta"] = {k: str(v) if isinstance(v, Path) else v for k, v in self.meta.items()}
        d["key"] = "|".join([self.kind, self.group, self.title, self.href or self.url or d["meta"].get("dir", "")])
        return d


def merge(registry: List[Item], canvases: List[Item], copy_paths: Dict[str, Path]) -> List[Item]:  # copy_paths: registry url -> folder
    """Join each registry item with the canvas in (or under) its Copy folder; keep the rest."""
    used = []
    out = []
    for r in registry:
        folder = copy_paths.get(r.url)
        c = next((c for c in canvases if folder and c not in used
                  and (c.meta["dir"] == folder or folder in c.meta["dir"].parents)), None)
        if c:
            used.append(c)
            r = replace(r, boards=list(c.boards))
        out.append(r)
    out.extend(c for c in canvases if c not in used)
    return out
