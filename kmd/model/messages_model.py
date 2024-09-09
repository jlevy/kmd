from textwrap import dedent

from kmd.config.logger import get_logger
from kmd.util.string_template import StringTemplate

log = get_logger(__name__)


class Message(str):
    """
    A message for a model or LLM. Just a string.
    """

    def __new__(cls, value: str):
        return super().__new__(cls, dedent(value))


class MessageTemplate(StringTemplate):
    """
    A template for an LLM request.
    """

    def __init__(self, template: str):
        super().__init__(dedent(template), allowed_fields=["body"])


# TODO: Consolidate as a new class.
# @dataclass(frozen=True)
# class LLMTemplate:
#     system_message: Message
#     template: MessageTemplate
#     title_template: Optional[TitleTemplate] = None
#     windowing: Optional[WindowSettings] = None
