import os
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

SANDBOX_NAME = "sandbox"
SANDBOX_KB_PATH = f"~/.local/kmd/{SANDBOX_NAME}.kb"


GLOBAL_CACHE_NAME = "kmd_cache"
MEDIA_CACHE_NAME = "media"
CONTENT_CACHE_NAME = "content"

LOCAL_SERVER_LOG_FILE = "~/.local/kmd/logs/server.log"
LOCAL_SERVER_PORT = 4477
"""The port to run the local server on. 4477 is not currently used by anything else."""


def resolve_and_create_dirs(path: Path | str, is_dir: bool = False) -> Path:
    """
    Resolve a path to an absolute path, handling ~ for the home directory
    and creating any missing parent directories.
    """
    full_path = Path(path).expanduser().resolve()
    if not full_path.exists():
        if is_dir:
            os.makedirs(full_path, exist_ok=True)
        else:
            os.makedirs(full_path.parent, exist_ok=True)
    return full_path


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

    local_server_host: str
    """The local hostname to run the local server on."""

    local_server_port: int
    """The port to run the local server on."""


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
    local_server_host="127.0.0.1",
    local_server_port=LOCAL_SERVER_PORT,
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
