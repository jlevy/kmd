import kmd.config.suppress_warnings  # noqa: F401
import os
from pathlib import Path
from typing import Any, Optional
import logging
from logging import INFO, WARNING, Formatter
from rich import reconfigure
from slugify import slugify
from strif import new_timestamped_uid, atomic_output_file
from rich.logging import RichHandler
from rich.theme import Theme
from rich.console import Console
from kmd.config.text_styles import EMOJI_SAVED, EMOJI_WARN, RICH_STYLES, KmdHighlighter

LOG_DIR_NAME = ".logs"
LOG_FILE_NAME = "kmd.log"
LOG_OBJECTS_NAME = "objects"

_log_root = Path(".")


def log_dir() -> Path:
    return _log_root / LOG_DIR_NAME


def log_file() -> Path:
    return log_dir() / LOG_FILE_NAME


def log_objects_dir() -> Path:
    return log_dir() / LOG_OBJECTS_NAME


# Rich console theme setup.
_custom_theme = Theme(RICH_STYLES)
_console = Console(theme=_custom_theme)
reconfigure(theme=_custom_theme)


def get_console():
    """A globally shared custom console for logging and output for interactive use."""

    return _console


# TODO: Need this to enforce flushing of stream?
# class FlushingStreamHandler(logging.StreamHandler):
#     def emit(self, record):
#         super().emit(record)
#         self.flush()


def logging_setup():
    """
    Set up or reset logging setup. Call at initial run and again if log directory changes.
    Replaces all previous loggers and handlers.
    """

    kmd.config.suppress_warnings.filter_warnings()

    os.makedirs(log_dir(), exist_ok=True)
    os.makedirs(log_objects_dir(), exist_ok=True)

    # Verbose logging to file, important logging to console.
    file_handler = logging.FileHandler(log_file())
    file_handler.setLevel(INFO)
    file_handler.setFormatter(Formatter("%(asctime)s %(levelname).1s %(name)s - %(message)s"))

    console_handler = RichHandler(
        console=_console,
        level=WARNING,
        show_time=False,
        show_path=False,
        show_level=False,
        highlighter=KmdHighlighter(),
        markup=True,
    )
    console_handler.setFormatter(Formatter("%(message)s"))

    from litellm import _logging  # noqa: F401

    for logger_name in [None, "LiteLLM", "LiteLLM Router", "LiteLLM Proxy"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(INFO)
        logger.propagate = True
        # Remove any existing handlers.
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)


def prefix_with_warn_emoji(line: str, emoji: str = EMOJI_WARN):
    if emoji not in line:
        return f"{emoji} {line}"
    return line


class CustomLogger:
    """
    Custom logger to be clearer about user messages and allow saving objects.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def message(self, *args, **kwargs):
        self.logger.warning(*args, **kwargs)

    def warning(self, *args, **kwargs):
        if len(args) > 0:
            args = (prefix_with_warn_emoji(args[0]),) + args[1:]
        self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        if len(args) > 0:
            args = (prefix_with_warn_emoji(args[0]),) + args[1:]
        self.logger.error(*args, **kwargs)

    def save_object(self, description: str, prefix_slug: Optional[str], obj: Any):
        prefix = prefix_slug + "." if prefix_slug else ""
        filename = f"{prefix}{slugify(description, separator='_')}.{new_timestamped_uid()}.txt"
        path = log_objects_dir() / filename
        with atomic_output_file(path) as tmp_filename:
            if isinstance(obj, bytes):
                with open(tmp_filename, "wb") as f:
                    f.write(obj)
            else:
                with open(tmp_filename, "w") as f:
                    f.write(str(obj))

        self.message("%s %s saved: %s", EMOJI_SAVED, description, path)

    def __getattr__(self, attr):
        return getattr(self.logger, attr)


def get_logger(name: str):
    return CustomLogger(name)


def reset_log_root(log_root: Path):
    global _log_root
    if log_root != _log_root:
        log = get_logger(__name__)
        log.info("Resetting log root: %s", log_file().absolute())

        _log_root = log_root
        logging_setup()
