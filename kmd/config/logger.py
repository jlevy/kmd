import threading
import kmd.config.suppress_warnings  # noqa: F401
import os
from pathlib import Path
from typing import Any, Literal, Optional
import logging
from logging import ERROR, INFO, WARNING, Formatter
from rich import reconfigure
from slugify import slugify
from strif import new_timestamped_uid, atomic_output_file
from rich.logging import RichHandler
from rich.theme import Theme
from rich.console import Console
from kmd.config.text_styles import EMOJI_SAVED, EMOJI_WARN, RICH_STYLES, KmdHighlighter
from kmd.text_formatting.text_formatting import fmt_path
from kmd.util.stack_traces import current_stack_traces
from kmd.util.task_stack import task_stack_prefix_str

LOG_DIR_NAME = ".kmd/logs"
LOG_FILE_NAME = "kmd.log"
LOG_OBJECTS_NAME = "objects"

_log_root = Path(".")

_log_lock = threading.Lock()


def log_dir() -> Path:
    return _log_root / LOG_DIR_NAME


def log_file_path() -> Path:
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

global _file_handler
global _console_handler


def logging_setup():
    """
    Set up or reset logging setup. Call at initial run and again if log directory changes.
    Replaces all previous loggers and handlers.
    """

    kmd.config.suppress_warnings.filter_warnings()

    os.makedirs(log_dir(), exist_ok=True)
    os.makedirs(log_objects_dir(), exist_ok=True)

    # Verbose logging to file, important logging to console.
    global _file_handler
    _file_handler = logging.FileHandler(log_file_path())
    _file_handler.setLevel(INFO)
    _file_handler.setFormatter(Formatter("%(asctime)s %(levelname).1s %(name)s - %(message)s"))

    global _console_handler
    _console_handler = RichHandler(
        console=_console,
        level=WARNING,
        show_time=False,
        show_path=False,
        show_level=False,
        highlighter=KmdHighlighter(),
        markup=True,
    )
    _console_handler.setFormatter(Formatter("%(message)s"))

    # Manually adjust logging for a few packages, removing previous verbose default handlers.
    from litellm import _logging  # noqa: F401
    from weasyprint import LOGGER, PROGRESS_LOGGER  # noqa: F401

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


def prefix(line, emoji: str = ""):
    prefix = task_stack_prefix_str()
    if prefix:
        prefix += " "
    if emoji:
        prefix = f"{prefix}{emoji} "
    return f"{prefix}{line}"


def prefix_args(args, emoji: str = ""):
    if len(args) > 0:
        args = (prefix(args[0], emoji),) + args[1:]
    return args


LogLevel = Literal["debug", "info", "message", "warning", "error"]


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
        self.logger.warning(*prefix_args(args, EMOJI_WARN), **kwargs)

    def error(self, *args, **kwargs):
        self.logger.error(*prefix_args(args, EMOJI_WARN), **kwargs)

    def log(self, level: LogLevel, *args, **kwargs):
        getattr(self, level)(*args, **kwargs)

    # Fallback for other attributes/methods.
    def __getattr__(self, attr):
        return getattr(self.logger, attr)

    def save_object(
        self, description: str, prefix_slug: Optional[str], obj: Any, level: LogLevel = "info"
    ):
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

        self.log(level, "%s %s saved: %s", EMOJI_SAVED, description, path)

    def dump_stack(self, all_threads: bool = True):
        self.logger.info("Stack trace dump:\n%s", current_stack_traces(all_threads))


def get_logger(name: str):
    return CustomLogger(name)


def get_log_file_stream():
    return _file_handler.stream


def reset_log_root(log_root: Path):
    global _log_lock
    with _log_lock:
        global _log_root
        if log_root != _log_root:
            log = get_logger(__name__)
            log.info("Resetting log root: %s", fmt_path(log_file_path().absolute()))

            _log_root = log_root
            logging_setup()
