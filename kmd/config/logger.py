import os
from pathlib import Path
from typing import Any, Optional
import warnings
import logging
from logging import INFO, WARNING, Formatter
from rich import reconfigure
from slugify import slugify
from strif import new_timestamped_uid, atomic_output_file
from rich.logging import RichHandler
from rich.theme import Theme
from rich.console import Console
from kmd.text_ui.text_styles import EMOJI_SAVED, EMOJI_WARN, HRULE, RICH_STYLES, KmdHighlighter

LOG_ROOT = Path("./.kmd_logs")

LOG_FILE = "kmd.log"

LOG_PATH = LOG_ROOT / LOG_FILE

LOG_OBJECTS = LOG_ROOT / "objects"


_custom_theme = Theme(RICH_STYLES)

console = Console(theme=_custom_theme)

reconfigure(theme=_custom_theme)

# TODO: Need this to enforce flushing of stream?
# class FlushingStreamHandler(logging.StreamHandler):
#     def emit(self, record):
#         super().emit(record)
#         self.flush()

def logging_setup():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    os.makedirs(LOG_ROOT, exist_ok=True)
    os.makedirs(LOG_OBJECTS, exist_ok=True)

    # Verbose logging to file, important logging to console.
    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setLevel(INFO)
    file_handler.setFormatter(Formatter("%(asctime)s %(levelname).1s %(name)s - %(message)s"))

    console_handler = RichHandler(level=WARNING, show_time=False, show_path=False, show_level=False, highlighter=KmdHighlighter(), markup=True)
    console_handler.setFormatter(Formatter("%(message)s"))

    root_logger = logging.getLogger()
    root_logger.setLevel(INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Customize the logger for LiteLLM.
    litellm_logger = logging.getLogger("LiteLLM")
    if litellm_logger.handlers:
        litellm_logger.setLevel(logging.INFO)
        # Remove any existing handlers.
        for handler in litellm_logger.handlers[:]:
            litellm_logger.removeHandler(handler)
        litellm_logger.addHandler(console_handler)
        litellm_logger.addHandler(file_handler)

    # TODO: Improve ytdl logging setup.


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

    def separator(self):
        self.message(HRULE)

    def save_object(self, description: str, prefix_slug: Optional[str], obj: Any):
        prefix = prefix_slug + "." if prefix_slug else ""
        filename = f"{prefix}{slugify(description, separator="_")}.{new_timestamped_uid()}.txt"
        path = LOG_OBJECTS / filename
        with atomic_output_file(path) as tmp_filename:
            with open(tmp_filename, "w") as f:
                f.write(str(obj))

        self.message("%s %s saved: %s", EMOJI_SAVED, description, path)

    def __getattr__(self, attr):
        return getattr(self.logger, attr)


def get_logger(name: str):
    return CustomLogger(name)
