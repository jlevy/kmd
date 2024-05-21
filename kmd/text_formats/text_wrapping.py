import textwrap
from typing import Optional
from kmd.model.items_model import Format


def wrap_text(text: str, format: Optional[Format] = None, width=80) -> str:
    """
    When saving plaintext or Markdown, wrap it by adding line breaks for readability.
    """
    if format == Format.plaintext:
        paragraphs = text.split("\n\n")
        wrapped_paragraphs = [
            textwrap.fill(p, width=width, break_long_words=False, replace_whitespace=False)
            for p in paragraphs
        ]
        return "\n\n".join(wrapped_paragraphs)
    # TODO: Add cleaner canonicalization/wrapping for Markdown. Also Flowmark?
    else:
        return text
