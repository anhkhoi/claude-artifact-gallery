"""Where the gallery keeps its generated files."""
import os
from pathlib import Path


def cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME", "")  # the XDG spec says to ignore empty or relative values
    base = Path(xdg) if xdg and Path(xdg).is_absolute() else Path.home() / ".cache"
    path = base / "claude-artifact-gallery"
    path.mkdir(parents=True, exist_ok=True)
    return path
