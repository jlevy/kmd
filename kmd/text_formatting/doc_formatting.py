import textwrap
from typing import Optional
from kmd.model.items_model import Format
from kmd.text_formatting.markdown_normalization import DEFAULT_WRAP_WIDTH, normalize_markdown


def wrap_plaintext(text: str, width=80) -> str:
    """
    When saving plaintext, wrap it by adding line breaks for readability.
    """
    paragraphs = text.split("\n\n")
    wrapped_paragraphs = [
        textwrap.fill(p, width=width, break_long_words=False, replace_whitespace=False)
        for p in paragraphs
    ]
    return "\n\n".join(wrapped_paragraphs)


def normalize_formatting(text: str, format: Optional[Format], width=DEFAULT_WRAP_WIDTH) -> str:
    """
    Normalize text formatting by wrapping lines and normalizing Markdown.
    """
    if format == Format.plaintext:
        return wrap_plaintext(text, width=width)
    elif format == Format.markdown:
        return normalize_markdown(text)
    elif format == Format.md_html or format == Format.html:
        # We don't currently format these as it's usually confusing.
        return text
    else:
        return text