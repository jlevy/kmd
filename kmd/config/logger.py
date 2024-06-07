import os
from pathlib import Path
from typing import Any, Optional
import warnings
import logging
from logging import INFO, WARNING, Formatter
import sys
from slugify import slugify
from strif import new_timestamped_uid, atomic_output_file
from kmd.config.text_styles import EMOJI_SAVED

LOG_ROOT = Path("./.kmd_logs")

LOG_FILE = "kmd.log"

LOG_PATH = LOG_ROOT / LOG_FILE

LOG_OBJECTS = LOG_ROOT / "objects"


def logging_setup():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    os.makedirs(LOG_ROOT, exist_ok=True)
    os.makedirs(LOG_OBJECTS, exist_ok=True)

    # Verbose logging to file, important logging to console.
    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setLevel(INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(WARNING)

    file_handler.setFormatter(Formatter("%(asctime)s %(levelname).1s %(name)s - %(message)s"))
    # TODO: Add colors!
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
