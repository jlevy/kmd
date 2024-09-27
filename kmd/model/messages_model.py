from textwrap import dedent

from pydantic import ValidationInfo

from kmd.config.logger import get_logger
from kmd.util.string_template import StringTemplate

log = get_logger(__name__)


class Message(str):
    """
    A message for a model or LLM. Just a string.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str, info: ValidationInfo) -> "Message":
        return cls(dedent(str(value)))


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
