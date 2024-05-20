import os
import tomllib
import openai
from cachetools import cached
from assertpy import assert_that

from kmd.config.logging import logging_setup
from kmd.config.settings import ROOT


@cached(cache={})
def setup():
    """One-time setup of essential keys, directories, and configs. Idempotent."""

    logging_setup()

    api_setup()


@cached(cache={})
def _load_secrets():
    paths = ["secrets.toml", f"{ROOT}/secrets/secrets.toml"]
    all_secrets = {}
    for path in reversed(paths):
        try:
            with open(path, "rb") as f:
                secrets = tomllib.load(f)
                all_secrets.update(secrets)
        except FileNotFoundError:
            continue

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
