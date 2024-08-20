from textwrap import dedent
from kmd.config.logger import get_logger
from kmd.util.string_template import StringTemplate


log = get_logger(__name__)


class LLMTemplate(StringTemplate):
    """A template for an LLM request."""

    def __init__(self, template: str):
        super().__init__(dedent(template), allowed_fields=["body"])


class LLMMessage(str):
    """A message for an LLM."""

    def __new__(cls, value: str):
        return super().__new__(cls, dedent(value))
