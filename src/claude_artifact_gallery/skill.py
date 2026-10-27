"""The /artifact-gallery-pull skill: where Claude Code profiles keep skills, and installing it into them."""
import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

NAME = "artifact-gallery-pull"
LEGACY_NAME = "pull"  # the first release installed it under this name; removed on install when it is ours
SRC = Path(__file__).parent / "skills" / NAME / "SKILL.md"


def current_profile() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def _looks_like_profile(path: Path) -> bool:
    return path.is_dir() and any((path / n).exists() for n in ("projects", "settings.json", "history.jsonl"))


def profiles() -> List[Path]:
    """The profile in effect, plus ~/.claude and ~/.claude-* when they look like a Claude Code config folder."""
    current = current_profile()
    out, seen = [], set()
    for p in [current, Path.home() / ".claude", *sorted(Path.home().glob(".claude-*"))]:
        key = p.resolve()
        if key not in seen and (p == current or _looks_like_profile(p)):
            seen.add(key)
            out.append(p)
    return out


def skill_file(skills_dir: Path, name: str = NAME) -> Path:
    return skills_dir / name / "SKILL.md"


def _legacy_ours(skills_dir: Path) -> Optional[Path]:
    legacy = skill_file(skills_dir, LEGACY_NAME)
    try:
        return legacy if legacy.exists() and "claude-artifact-gallery" in legacy.read_text(encoding="utf-8") else None
    except (OSError, ValueError):
        return None


def is_installed(skills_dir: Path) -> bool:
    return skill_file(skills_dir).exists() or _legacy_ours(skills_dir) is not None


def is_current(skills_dir: Path) -> bool:
    dest = skill_file(skills_dir)
    try:
        return dest.exists() and dest.read_bytes() == SRC.read_bytes() and _legacy_ours(skills_dir) is None
    except OSError:
        return False


def outdated_profiles() -> List[Path]:
    """Profiles that have the skill installed, but not the packaged version of it."""
    return [p for p in profiles() if is_installed(p / "skills") and not is_current(p / "skills")]


def install(skills_dir: Path, force: bool) -> Tuple[str, Path, Optional[Path]]:
    """-> ("installed" | "current" | "conflict", skill file, legacy file removed or None)."""
    dest = skill_file(skills_dir)
    if dest.exists() and dest.read_bytes() == SRC.read_bytes():
        status = "current"
    elif dest.exists() and not force:
        return "conflict", dest, None
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SRC, dest)
        status = "installed"
    legacy = _legacy_ours(skills_dir)
    if legacy:
        legacy.unlink()
        try:
            legacy.parent.rmdir()
        except OSError:
            pass
    return status, dest, legacy
