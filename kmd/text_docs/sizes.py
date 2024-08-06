from enum import Enum
from kmd.config.logger import get_logger
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

    BYTES = "bytes"
    CHARS = "chars"
    WORDS = "words"
    WORDTOKS = "wordtoks"
    PARAGRAPHS = "paragraphs"
    SENTENCES = "sentences"


def size(text: str, unit: TextUnit) -> int:
    if unit == TextUnit.BYTES:
        return size_in_bytes(text)
    elif unit == TextUnit.CHARS:
        return len(text)
    elif unit == TextUnit.WORDS:
        # Roughly accurate for HTML, text, or Markdown docs.
        return len(html_to_plaintext(text).split())
    elif unit == TextUnit.WORDTOKS:
        return size_in_wordtoks(text)
    else:
        raise UnexpectedError(f"Unsupported unit for string: {unit}")
