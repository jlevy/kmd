import threading
from contextlib import contextmanager
from enum import Enum
from logging import DEBUG, ERROR, INFO, WARNING
from pathlib import Path
from typing import Optional

from cachetools import cached
from pydantic.dataclasses import dataclass


APP_NAME = "kmd"

DOT_DIR = ".kmd"

SANDBOX_KB_PATH = "~/.local/kmd/sandbox.kb"

GLOBAL_CACHE_NAME = "kmd_cache"
MEDIA_CACHE_NAME = "media"
CONTENT_CACHE_NAME = "content"


class LogLevel(Enum):
    debug = DEBUG
    info = INFO
    warning = WARNING
    message = WARNING  # Same as warning, just for important console messages.
    error = ERROR

    @classmethod
    def parse(cls, level_str: str):
        canon_name = level_str.strip().lower()
        if canon_name == "warn":
            canon_name = "warning"
        try:
            return cls[canon_name]
        except KeyError:
            raise ValueError(
                f"Invalid log level: `{level_str}`. Valid options are: {', '.join(f'`{name}`' for name in cls.__members__)}"
            )

    def __str__(self):
        return self.name


@dataclass
class Settings:
    media_cache_dir: Path
    """The media cache directory, for caching audio, video, and transcripts."""

    content_cache_dir: Path
    """The content cache directory, for caching web or local files."""

    debug_assistant: bool
    """Convenience to allow debugging of full assistant prompts."""

    default_editor: str
    """The default editor to use for editing files."""

    use_sandbox: bool
    """If not in a workspace, use the sandbox workspace."""

    console_log_level: LogLevel
    """The log level for console-based logging."""

    file_log_level: LogLevel
    """The log level for file-based logging."""


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
def _global_cache_dir(name: str) -> Path:
    cache_dir = find_in_cwd_or_parents(GLOBAL_CACHE_NAME)
    if not cache_dir:
        cache_dir = Path(".").absolute() / GLOBAL_CACHE_NAME

    return cache_dir / name


# Initial default settings.
_settings = Settings(
    # These default to the global
    media_cache_dir=_global_cache_dir(MEDIA_CACHE_NAME),
    content_cache_dir=_global_cache_dir(CONTENT_CACHE_NAME),
    debug_assistant=True,
    default_editor="nano",
    use_sandbox=True,
    file_log_level=LogLevel.info,
    console_log_level=LogLevel.warning,
)


def global_settings() -> Settings:
    """
    Read access to global settings.
    """
    return _settings


_settings_lock = threading.Lock()


@contextmanager
def update_global_settings():
    """
    Context manager for thread-safe updates to global settings.
    """
    with _settings_lock:
        yield _settings
