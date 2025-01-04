import logging
import os
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from logging import ERROR, Formatter, INFO
from pathlib import Path
from typing import Any, IO, Optional

import rich
from rich import reconfigure
from rich._null_file import NULL_FILE
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from slugify import slugify

import kmd.config.suppress_warnings  # noqa: F401
from kmd.config.settings import global_settings, LogLevel
from kmd.config.text_styles import (
    EMOJI_ERROR,
    EMOJI_SAVED,
    EMOJI_WARN,
    KmdHighlighter,
    RICH_STYLES,
)
from kmd.util.format_utils import fmt_path
from kmd.util.stack_traces import current_stack_traces
from kmd.util.strif import atomic_output_file, new_timestamped_uid
from kmd.util.task_stack import task_stack_prefix_str

LOG_DIR_NAME = ".kmd/logs"
LOG_FILE_NAME = "kmd.log"
LOG_OBJECTS_NAME = "objects"

_log_root = Path(".")

_log_lock = threading.RLock()


def log_dir() -> Path:
    return _log_root / LOG_DIR_NAME


def log_file_path() -> Path:
    return log_dir() / LOG_FILE_NAME


def log_objects_dir() -> Path:
    return log_dir() / LOG_OBJECTS_NAME


@dataclass
class TlContext(threading.local):
    console: Optional[Console] = None


_tl_context = TlContext()
"""
Thread-local context override for Rich console.
"""


@cache
def get_highlighter():
    return KmdHighlighter()


@cache
def get_theme():
    return Theme(RICH_STYLES)


reconfigure(theme=get_theme(), highlighter=get_highlighter())


def get_console() -> Console:
    """
    Return the Rich global console, unless it is overridden by a
    thread-local console.
    """
    return _tl_context.console or rich.get_console()


def new_console(file: Optional[IO[str]], record: bool) -> Console:
    """
    Create a new console with the our theme and highlighter.
    Use `get_console()` for the global console.
    """
    return Console(theme=get_theme(), highlighter=get_highlighter(), file=file, record=record)


@contextmanager
def record_console() -> Generator[Console, None, None]:
    """
    Context manager to temporarily override the global console with a thread-local
    console that records output.
    """
    old_console = _tl_context.console
    console = new_console(file=NULL_FILE, record=True)
    _tl_context.console = console

    try:
        yield console
    finally:
        _tl_context.console = old_console


# TODO: Need this to enforce flushing of stream?
# class FlushingStreamHandler(logging.StreamHandler):
#     def emit(self, record):
#         super().emit(record)
#         self.flush()

global _file_handler
global _console_handler


def logging_setup():
    """
    Set up or reset logging setup. Call at initial run and again if log directory changes.
    Replaces all previous loggers and handlers. Can be called to reset with different
    settings.
    """

    kmd.config.suppress_warnings.filter_warnings()

    os.makedirs(log_dir(), exist_ok=True)
    os.makedirs(log_objects_dir(), exist_ok=True)

    # Verbose logging to file, important logging to console.
    global _file_handler
    _file_handler = logging.FileHandler(log_file_path())
    _file_handler.setLevel(global_settings().file_log_level.value)
    _file_handler.setFormatter(Formatter("%(asctime)s %(levelname).1s %(name)s - %(message)s"))

    class PrefixedRichHandler(RichHandler):
        def emit(self, record):
            # Can add an extra indent to differentiate logs but it's a little messier looking.
            # record.msg = EMOJI_MSG_INDENT + record.msg
            super().emit(record)

    global _console_handler
    _console_handler = PrefixedRichHandler(
        # For now we use the fixed global console for logging.
        # In the ruture we may want to add a way to have thread-local capture
        # of all system logs.
        console=rich.get_console(),
        level=global_settings().console_log_level.value,
        show_time=False,
        show_path=False,
        show_level=False,
        highlighter=get_highlighter(),
        markup=True,
    )
    _console_handler.setLevel(global_settings().console_log_level.value)
    _console_handler.setFormatter(Formatter("%(message)s"))

    # Manually adjust logging for a few packages, removing previous verbose default handlers.

    import litellm
    from litellm import _logging  # noqa: F401
    from weasyprint import LOGGER, PROGRESS_LOGGER  # noqa: F401

    litellm.suppress_debug_info = True  # Suppress overly prominent exception messages.

    log_levels = {
        None: INFO,
        "LiteLLM": INFO,
        "LiteLLM Router": INFO,
        "LiteLLM Proxy": INFO,
        "weasyprint": ERROR,
        "weasyprint.progress": ERROR,
    }

    for logger_name, level in log_levels.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.propagate = True
        # Remove any existing handlers.
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.addHandler(_console_handler)
        logger.addHandler(_file_handler)


def prefix(line, emoji: str = "", warn_emoji: str = ""):
    prefix = task_stack_prefix_str()
    emojis = f"{warn_emoji}{emoji}".strip()
    return " ".join(filter(None, [prefix, emojis, line]))


def prefix_args(args, emoji: str = "", warn_emoji: str = ""):
    if len(args) > 0:
        args = (prefix(args[0], emoji, warn_emoji),) + args[1:]
    return args


class CustomLogger:
    """
    Custom logger to be clearer about user messages and allow saving objects.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def debug(self, *args, **kwargs):
        self.logger.debug(*prefix_args(args), **kwargs)

    def info(self, *args, **kwargs):
        self.logger.info(*prefix_args(args), **kwargs)

    def message(self, *args, **kwargs):
        self.logger.warning(*prefix_args(args), **kwargs)

    def warning(self, *args, **kwargs):
        self.logger.warning(*prefix_args(args, warn_emoji=EMOJI_WARN), **kwargs)

    def error(self, *args, **kwargs):
        self.logger.error(*prefix_args(args, warn_emoji=EMOJI_ERROR), **kwargs)

    def log(self, level: LogLevel, *args, **kwargs):
        getattr(self, level.name)(*args, **kwargs)

    # Fallback for other attributes/methods.
    def __getattr__(self, attr):
        return getattr(self.logger, attr)

    def save_object(
        self,
        description: str,
        prefix_slug: Optional[str],
        obj: Any,
        level: LogLevel = LogLevel.info,
        file_ext: str = "txt",
    ):
        prefix = prefix_slug + "." if prefix_slug else ""
        filename = (
            f"{prefix}{slugify(description, separator='_')}."
            f"{new_timestamped_uid()}.{file_ext.lstrip('.')}"
        )
        path = log_objects_dir() / filename
        with atomic_output_file(path) as tmp_filename:
            if isinstance(obj, bytes):
                with open(tmp_filename, "wb") as f:
                    f.write(obj)
            else:
                with open(tmp_filename, "w") as f:
                    f.write(str(obj))

        self.log(level, "%s %s saved: %s", EMOJI_SAVED, description, path)

    def dump_stack(self, all_threads: bool = True):
        self.logger.info("Stack trace dump:\n%s", current_stack_traces(all_threads))


def get_logger(name: str):
    return CustomLogger(name)


def get_log_file_stream():
    return _file_handler.stream


def reset_logging(log_root: Optional[Path] = None):
    """
    Reset the logging root, if it has changed.
    """
    global _log_lock
    with _log_lock:
        global _log_root
        if log_root and log_root != _log_root:
            log = get_logger(__name__)
            log.info("Resetting log root: %s", fmt_path(log_file_path().absolute()))

            _log_root = log_root

        logging_setup()
