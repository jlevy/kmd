import os
from pathlib import Path
import tomllib
import openai
from cachetools import cached
from assertpy import assert_that
from kmd.config.logger import logging_setup
from kmd.config.settings import find_in_cwd_or_parents


@cached(cache={})
def setup():
    """One-time setup of essential keys, directories, and configs. Idempotent."""

    logging_setup()

    api_setup()


# Look for API key secrets in these files.
SECRETS_FILE = "secrets.toml"
SECRETS_RC_FILE = "~/.secrets.toml"


@cached(cache={})
def _load_secrets():
    secrets_paths = []

    cwd_secrets = find_in_cwd_or_parents(SECRETS_FILE)
    home_secrets = Path(SECRETS_RC_FILE).expanduser()

    if home_secrets.exists():
        secrets_paths.append(home_secrets)
    if cwd_secrets:
        secrets_paths.append(cwd_secrets)

    # Merge secrets in cwd or parents with the one in the home directory.
    all_secrets = {}
    for path in secrets_paths:
        with open(path, "rb") as f:
            secrets = tomllib.load(f)
            all_secrets.update(secrets)

    if not all_secrets:
        from kmd.config.logger import get_logger

        log = get_logger(__name__)
        log.error(
            "Could not find secrets file in %s",
            ", ".join(str(p) for p in secrets_paths),
        )
    return all_secrets


def get_secret(name):
    """Get a secret from one or more secrets.toml files."""

    all_secrets = _load_secrets()
    if name in all_secrets:
        return all_secrets[name]
    else:
        raise KeyError(f"Secret '{name}' not found in the loaded secrets")


@cached(cache={})
def api_setup():
    secret_openai = get_secret("secret_openai")
    assert_that(
        secret_openai, "OpenAI secret not found in secrets.toml"
    ).is_not_none().is_not_empty()
    os.environ["OPENAI_API_KEY"] = secret_openai
    openai.api_key = secret_openai

    secret_deepgram = get_secret("secret_deepgram")
    assert_that(
        secret_deepgram, "Deepgram secret not found in secrets.toml"
    ).is_not_none().is_not_empty()
    os.environ["DEEPGRAM_API_KEY"] = secret_deepgram
