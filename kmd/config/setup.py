import os
from typing import Any

from cachetools import cached
from dotenv import find_dotenv, load_dotenv

from kmd.config.logger import logging_setup
from kmd.util.stack_traces import add_stacktrace_handler


def error(msg: str, *args: Any):
    from kmd.config.logger import get_logger

    log = get_logger(__name__)
    log.error(msg, *args)


@cached(cache={})
def setup():
    """
    One-time setup of essential keys, directories, and configs. Idempotent.
    """

    logging_setup()

    add_stacktrace_handler()

    api_setup()


RECOMMENDED_APIS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPGRAM_API_KEY", "GROQ_API_KEY"]


def api_setup():
    load_dotenv(find_dotenv(usecwd=True))

    for key in RECOMMENDED_APIS:
        if key not in os.environ:
            error(
                f"Error: Missing expected API key (check if it is set in environment or .env file?): {key}"
            )
