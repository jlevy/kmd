from enum import Enum
from kmd.config.logger import get_logger
from kmd.text_docs.tiktoken_utils import tiktoken_len
from kmd.text_formatting.text_formatting import html_to_plaintext
from kmd.model.errors_model import UnexpectedError
from kmd.text_docs.wordtoks import (
    raw_text_to_wordtoks,
)

log = get_logger(__name__)


def size_in_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def size_in_wordtoks(text: str) -> int:
    return len(raw_text_to_wordtoks(text))


class TextUnit(Enum):
    """
    Text units of measure.
    """

    bytes = "bytes"
    chars = "chars"
    words = "words"
    wordtoks = "wordtoks"
    paragraphs = "paragraphs"
    sentences = "sentences"
    tiktokens = "tiktokens"


def size(text: str, unit: TextUnit) -> int:
    if unit == TextUnit.bytes:
        return size_in_bytes(text)
    elif unit == TextUnit.chars:
        return len(text)
    elif unit == TextUnit.words:
        # Roughly accurate for HTML, text, or Markdown docs.
        return len(html_to_plaintext(text).split())
    elif unit == TextUnit.wordtoks:
        return size_in_wordtoks(text)
    elif unit == TextUnit.tiktokens:
        return tiktoken_len(text)
    else:
        raise UnexpectedError(f"Unsupported unit for string: {unit}")
