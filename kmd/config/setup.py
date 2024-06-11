import os
from pathlib import Path
import tomllib
from typing import Any
import openai
from cachetools import cached
from kmd.config.logger import logging_setup
from kmd.config.settings import find_in_cwd_or_parents
from kmd.util.stack_traces import add_stacktrace_handler
from kmd.util.thread_utils import synchronized


@cached(cache={})
def setup():
    """One-time setup of essential keys, directories, and configs. Idempotent."""

    logging_setup()

    add_stacktrace_handler()

    api_setup()


# Look for API key secrets in these files.
SECRETS_FILE = "secrets.toml"
SECRETS_RC_FILE = "~/.secrets.toml"


_secrets_info = ""


def error(msg: str, *args: Any):
    from kmd.config.logger import get_logger

    log = get_logger(__name__)
    log.error(msg, *args)


@synchronized
@cached(cache={})
def _load_secrets() -> dict[str, str]:
    secrets_paths = []

    cwd_secrets = find_in_cwd_or_parents(SECRETS_FILE)
    home_secrets = Path(SECRETS_RC_FILE).expanduser()

    if home_secrets.exists():
        secrets_paths.append(home_secrets)
    if cwd_secrets:
        secrets_paths.append(cwd_secrets)

    # Merge secrets in cwd or parents with the one in the home directory.
    all_secrets: dict[str, str] = {}
    for path in secrets_paths:
        with open(path, "rb") as f:
            secrets = tomllib.load(f)
            for key, value in secrets.items():
                if not value:
                    raise KeyError(f"Secret '{key}' in {path} is not set")
                if not isinstance(value, str):
                    raise KeyError(f"Secret '{key}' in {path} is not a string: {value}")
            all_secrets.update(secrets)

    global _secrets_info
    _secrets_info = f"{len(all_secrets)} secrets from {', '.join(str(p) for p in secrets_paths)}"
    if not all_secrets:
        error("Could not find secrets file in %s", ", ".join(str(p) for p in secrets_paths))
    return all_secrets


def get_secret(name) -> str:
    """
    Get a secret from one or more secrets.toml files. Raises KeyError if not found or invalid.
    """

    all_secrets = _load_secrets()
    if name in all_secrets:
        return all_secrets[name]
    else:
        error("Secret '%s' not found (loaded %s)", name, _secrets_info)
        raise KeyError(f"Secret missing: '{name}'")


@cached(cache={})
def api_setup():
    secret_openai = get_secret("secret_openai")
    os.environ["OPENAI_API_KEY"] = secret_openai

    secret_anthropic = get_secret("secret_anthropic")
    os.environ["ANTHROPIC_API_KEY"] = secret_anthropic

    secret_deepgram = get_secret("secret_deepgram")
    os.environ["DEEPGRAM_API_KEY"] = secret_deepgram

    secret_groq = get_secret("secret_groq")
    os.environ["GROQ_API_KEY"] = secret_groq
