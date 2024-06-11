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
from rich.highlighter import RegexHighlighter, _combine_regex
from rich.theme import Theme
from rich.console import Console
from kmd.config.text_styles import EMOJI_SAVED, RICH_STYLES

LOG_ROOT = Path("./.kmd_logs")

LOG_FILE = "kmd.log"

LOG_PATH = LOG_ROOT / LOG_FILE

LOG_OBJECTS = LOG_ROOT / "objects"


class KmdHighlighter(RegexHighlighter):
    """Highlights the text typically produced from ``__repr__`` methods."""

    base_style = "kmd."
    highlights = [
        r"(?P<tag_start><)(?P<tag_name>[-\w.:|]*)(?P<tag_contents>[\w\W]*)(?P<tag_end>>)",
        r'(?P<attrib_name>[\w_-]{1,50})=(?P<attrib_value>"?[\w_]+"?)?',
        r"(?P<brace>[][{}()])",
        _combine_regex(
            r"(?P<ipv4>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            r"(?P<ipv6>([A-Fa-f0-9]{1,4}::?){1,7}[A-Fa-f0-9]{1,4})",
            r"(?P<eui64>(?:[0-9A-Fa-f]{1,2}-){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){3}[0-9A-Fa-f]{4})",
            r"(?P<eui48>(?:[0-9A-Fa-f]{1,2}-){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})",
            r"(?P<uuid>[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
            r"(?P<call>[\w.]*?)\(",
            r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
            r"(?P<ellipsis>(\.\.\.|…))",
            r"(?P<number_complex>(?<!\w)(?:\-?[0-9]+\.?[0-9]*(?:e[-+]?\d+?)?)(?:[-+](?:[0-9]+\.?[0-9]*(?:e[-+]?\d+)?))?j)",
            r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b(?!\-\w)|0x[0-9a-fA-F]*)",
            r"(?P<duration>(?<!\w)\-?[0-9]+\.?[0-9]*(ms|s)\b(?!\-\w))",
            r"(?P<path>\B(/[-\w._+]+)*\/)(?P<filename>[-\w._+]*)?",
            r"(?<![\\\w])(?P<str>b?'''.*?(?<!\\)'''|b?'.*?(?<!\\)'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
            r"(?P<url>(file|https|http|ws|wss)://[-0-9a-zA-Z$_+!`(),.?/;:&=%#~]*)",
        ),
    ]

_custom_theme = Theme(RICH_STYLES)

console = Console(theme=_custom_theme)

reconfigure(theme=_custom_theme)


def logging_setup():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    os.makedirs(LOG_ROOT, exist_ok=True)
    os.makedirs(LOG_OBJECTS, exist_ok=True)

    # Verbose logging to file, important logging to console.
    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setLevel(INFO)
    file_handler.setFormatter(Formatter("%(asctime)s %(levelname).1s %(name)s - %(message)s"))

    console_handler = RichHandler(level=WARNING, show_time=False, show_path=False, show_level=False, highlighter=KmdHighlighter())
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


class CustomLogger:
    """
    Custom logger to be clearer about user messages and allow saving objects.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def message(self, *args, **kwargs):
        self.logger.warning(*args, **kwargs)

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
