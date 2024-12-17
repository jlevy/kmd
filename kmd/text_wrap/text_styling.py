from enum import Enum
from typing import List

import regex

from kmd.config.text_styles import CONSOLE_WRAP_WIDTH
from kmd.text_wrap.text_wrapping import html_md_word_splitter, WordSplitter, wrap_paragraph


DEFAULT_INDENT = "    "


def split_paragraphs(text: str) -> List[str]:
    return [p.strip() for p in regex.split(r"\n{2,}", text)]


class Wrap(Enum):
    """
    A few standard text wrapping styles.
    """

    NONE = "none"
    """No wrapping."""

    WRAP = "wrap"
    """Basic wrapping but preserves whitespace within paragraphs."""

    WRAP_FULL = "wrap_full"
    """Wraps and also normalizes whitespace."""

    WRAP_INDENT = "wrap_indent"
    """Wrap and also indent."""

    INDENT_ONLY = "indent_only"
    """Just indent."""

    HANGING_INDENT = "hanging_indent"
    """Wrap with hanging indent (indented except for the first line)."""

    @property
    def initial_indent(self) -> str:
        if self in [Wrap.INDENT_ONLY, Wrap.WRAP_INDENT]:
            return DEFAULT_INDENT
        else:
            return ""

    @property
    def subsequent_indent(self) -> str:
        if self in [Wrap.INDENT_ONLY, Wrap.WRAP_INDENT, Wrap.HANGING_INDENT]:
            return DEFAULT_INDENT
        else:
            return ""

    @property
    def should_wrap(self) -> bool:
        return self in [Wrap.WRAP, Wrap.WRAP_FULL, Wrap.WRAP_INDENT, Wrap.HANGING_INDENT]

    @property
    def replace_whitespace(self) -> bool:
        return self in [Wrap.WRAP_FULL, Wrap.WRAP_INDENT, Wrap.HANGING_INDENT]


def fill_text(
    text: str,
    text_wrap=Wrap.WRAP,
    extra_indent: str = "",
    empty_indent: str = "",
    width=CONSOLE_WRAP_WIDTH,
    splitter: WordSplitter = html_md_word_splitter,
) -> str:
    """
    Most flexible way to wrap and fill any number of paragraphs of plain text, with
    both text wrap options and extra indentation. Use for plain text. By default,
    uses an HTML and Markdown aware word splitter.
    """

    if not text_wrap.should_wrap:
        indent = extra_indent + DEFAULT_INDENT if text_wrap == Wrap.INDENT_ONLY else extra_indent
        lines = text.splitlines()
        if lines:
            return "\n".join(indent + line for line in lines)
        else:
            return empty_indent
    else:
        # Common settings for all wrap modes.
        empty_indent = empty_indent.strip()
        initial_indent = extra_indent + text_wrap.initial_indent
        subsequent_indent = extra_indent + text_wrap.subsequent_indent

        # These vary by wrap mode.
        width = width - len(subsequent_indent)
        replace_whitespace = text_wrap.replace_whitespace

        paragraphs = split_paragraphs(text)
        wrapped_paragraphs = []

        # Wrap each paragraph.
        for i, paragraph in enumerate(paragraphs):
            # Special case for hanging indent mode.
            # Hang the first line of the first paragraph. All other paragraphs are indented.
            if text_wrap == Wrap.HANGING_INDENT and i > 0:
                initial_indent = subsequent_indent

            wrapped_paragraphs.append(
                wrap_paragraph(
                    paragraph,
                    width=width,
                    initial_indent=initial_indent,
                    subsequent_indent=subsequent_indent,
                    replace_whitespace=replace_whitespace,
                    splitter=splitter,
                )
            )

        para_sep = f"\n{empty_indent}\n"
        return para_sep.join(wrapped_paragraphs)
