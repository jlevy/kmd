from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from cachetools import cached


APP_NAME = "kmd"

GLOBAL_CACHE_NAME = "kmd_cache"


@dataclass
class Settings:
    media_cache_dir: Path
    """The media cache directory."""

    web_cache_dir: Path
    """The web cache directory."""

    debug_assistant: bool
    """Convenience to allow debugging of full assistant prompts."""


def find_in_cwd_or_parents(filename: Path | str) -> Optional[Path]:
    """
    Find the first existing Path (or None) for a given filename in the current directory or its parents.
    """
    if isinstance(filename, str):
        filename = Path(filename)
    path = Path(".").absolute()
    while path != Path("/"):
        file_path = path / filename
        if file_path.exists():
            return file_path
        path = path.parent
    return None


@cached(cache={})
def _cache_dir(name: str = "") -> Path:
    cache_dir = find_in_cwd_or_parents(GLOBAL_CACHE_NAME)
    if not cache_dir:
        cache_dir = Path(".").absolute() / GLOBAL_CACHE_NAME

    return cache_dir / name


# Initial default settings.
_settings = Settings(
    media_cache_dir=_cache_dir("media"),
    web_cache_dir=_cache_dir("web"),
    debug_assistant=False,
)


def get_settings() -> Settings:
    return _settings
