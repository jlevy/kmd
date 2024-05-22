import warnings
import logging
from logging import INFO, WARNING, Formatter
import sys

from kmd.config.settings import APP_NAME

# TODO: Add rich logging


def logging_setup():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    # Verbose logging to file, important logging to console.
    file_handler = logging.FileHandler(f"{APP_NAME}.log")
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


class CustomLogger:
    """
    Custom logger simply to be clearer about user messages vs info/warning.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def message(self, *args, **kwargs):
        self.logger.warning(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self.logger, attr)


def get_logger(name: str):
    return CustomLogger(name)
