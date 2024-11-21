import os
from enum import Enum
from threading import Event
from typing import Any

from cachetools import cached
from dotenv import find_dotenv, load_dotenv

from kmd.config.logger import logging_setup
from kmd.util.stack_traces import add_stacktrace_handler


@cached(cache={})
def setup():
    """
    One-time setup of essential keys, directories, and configs. Idempotent.
    """

    logging_setup()

    lib_setup()

    add_stacktrace_handler()

    api_setup()


RECOMMENDED_APIS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPGRAM_API_KEY", "GROQ_API_KEY"]


def api_setup() -> str | None:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path)
    return dotenv_path


_log_api_setup_done = Event()


def log_api_key_setup(once: bool = False) -> None:
    if once and _log_api_setup_done.is_set():
        return

    from kmd.config.logger import get_logger

    log = get_logger(__name__)

    dotenv_path = api_setup()

    if dotenv_path:
        log.message("Found .env file for API keys: %s", dotenv_path)
    else:
        log.warning("No .env file found. Set up your API keys in a .env file.")

    for key in RECOMMENDED_APIS:
        if key not in os.environ:
            log.warning("Missing recommended API key: %s", key)

    _log_api_setup_done.set()


def lib_setup():
    from frontmatter_format.yaml_util import add_default_yaml_customizer
    from ruamel.yaml import Representer

    def represent_enum(dumper: Representer, data: Enum) -> Any:
        """
        Represent Enums as their values.
        Helps make it easy to serialize enums to YAML everywhere.
        We use the convention of storing enum values as readable strings.
        """
        return dumper.represent_str(data.value)

    add_default_yaml_customizer(
        lambda yaml: yaml.representer.add_multi_representer(Enum, represent_enum)
    )

    # Maybe useful?

    # from pydantic import BaseModel

    # def represent_pydantic(dumper: Representer, data: BaseModel) -> Any:
    #     """Represent Pydantic models as YAML dictionaries."""
    #     return dumper.represent_dict(data.model_dump())

    # add_default_yaml_customizer(
    #     lambda yaml: yaml.representer.add_multi_representer(BaseModel, represent_pydantic)
    # )
