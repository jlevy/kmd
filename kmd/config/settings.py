from pathlib import Path
from typing import Optional
from cachetools import cached


APP_NAME = "kmd"

CACHE_NAME = "kmd_cache"

DEBUG_ASSISTANT = False
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
def cache_dir(name: str) -> Path:
    """
    The media cache directory. Set at load time and used for the entire session.
    """
    cache_dir = find_in_cwd_or_parents(CACHE_NAME)
    if not cache_dir:
        cache_dir = Path(".").absolute() / CACHE_NAME

    return cache_dir / name


def media_cache_dir() -> Path:
    """
    The media cache directory. Set at load time and used for the entire session.
    """
    return cache_dir("media")


def web_cache_dir() -> Path:
    """
    The web cache directory. Set at load time and used for the entire session.
    """
    return cache_dir("web")
