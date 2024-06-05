from pathlib import Path
from typing import Optional
from cachetools import cached


APP_NAME = "kmd"

CACHE_NAME = "kmd_cache"

KMD_WRAP_WIDTH = 80
"""Wrap width for kmd output."""

DEFAULT_WRAP_WIDTH = 92
"""Default wrap width for text content."""


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
def media_cache_dir() -> str:
    """
    The media cache directory. Set at load time and used for the entire session.
    """
    cache_dir = find_in_cwd_or_parents(CACHE_NAME)
    if not cache_dir:
        cache_dir = Path(".").absolute() / CACHE_NAME

    return str(cache_dir / "media")
