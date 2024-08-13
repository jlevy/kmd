"""
Output methods. These are for user interaction, not logging.
"""

from io import StringIO
import threading
import sys
from contextlib import contextmanager
from enum import Enum
import textwrap
from textwrap import dedent, indent
from typing import Any, Callable, Optional
import rich
from rich.text import Text
from kmd.config.logger import get_console
from kmd.text_formatting.markdown_normalization import normalize_markdown, wrap_lines_to_width
from kmd.config.text_styles import (
    COLOR_ASSISTANCE,
    COLOR_HEADING,
    COLOR_HINT,
    COLOR_KEY,
    COLOR_OUTPUT,
    COLOR_PLAIN,
    COLOR_RESPONSE,
    CONSOLE_WRAP_WIDTH,
    EMOJI_ASSISTANT,
    HRULE,
)

console = get_console()


class Wrap(Enum):
    NONE = "none"
    WRAP = "wrap"  # Basic wrapping but preserves whitespace.
    WRAP_FULL = "wrap_full"  # Also replaces whitespace.
    WRAP_INDENT = "wrap_indent"  # Wrap and indent.
    INDENT_ONLY = "indent_only"  # Just indent.
    HANGING_INDENT = "hanging_indent"  # Wrap with hanging indent.


def fill_text(text: str, text_wrap=Wrap.WRAP) -> str:
    if text_wrap == Wrap.NONE:
        return text
    elif text_wrap == Wrap.INDENT_ONLY:
        return indent(text, prefix="    ")
    elif text_wrap in [Wrap.WRAP, Wrap.WRAP_FULL, Wrap.WRAP_INDENT, Wrap.HANGING_INDENT]:
        paragraphs = text.split("\n\n")
        wrapped_paragraphs = []

        for paragraph in paragraphs:
            if text_wrap == Wrap.WRAP:
                wrapped_paragraphs.append(
                    textwrap.fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH,
                        replace_whitespace=False,
                        break_long_words=False,
                        break_on_hyphens=False,
                    )
                )
            elif text_wrap == Wrap.WRAP_FULL:
                wrapped_paragraphs.append(
                    textwrap.fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH,
                        replace_whitespace=True,
                        break_long_words=False,
                        break_on_hyphens=False,
                    )
                )
            elif text_wrap == Wrap.WRAP_INDENT:
                wrapped_paragraphs.append(
                    textwrap.fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH - 4,
                        initial_indent="    ",
                        subsequent_indent="    ",
                        replace_whitespace=True,
                        break_long_words=False,
                        break_on_hyphens=False,
                    )
                )
            elif text_wrap == Wrap.HANGING_INDENT:
                wrapped_paragraphs.append(
                    textwrap.fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH - 8,
                        initial_indent="",
                        subsequent_indent="    ",
                        replace_whitespace=True,
                        break_long_words=False,
                        break_on_hyphens=False,
                    )
                )

        return "\n\n".join(wrapped_paragraphs)
    else:
        raise ValueError(f"Unknown text_wrap value: {text_wrap}")


def fill_markdown(doc_str: str):
    return normalize_markdown(dedent(doc_str).strip(), line_wrapper=wrap_lines_to_width)


def format_name_and_description(name: str, doc: str, parenthetical: Optional[str] = None) -> Text:
    doc = textwrap.dedent(doc).strip()
    wrapped = fill_text(doc, text_wrap=Wrap.WRAP_INDENT)
    return Text.assemble(
        ("`", COLOR_HINT),
        (name, COLOR_KEY),
        ("`", COLOR_HINT),
        ((" " + parenthetical, COLOR_PLAIN) if parenthetical else ""),
        (": ", COLOR_HINT),
        "\n",
        (wrapped, COLOR_PLAIN),
    )


# Allow output stream to be redirected if desired.
_output_context = threading.local()
_output_context.stream = None


@contextmanager
def redirect_output(new_output):
    old_output = getattr(_output_context, "stream", sys.stdout)
    _output_context.stream = new_output
    try:
        yield
    finally:
        _output_context.stream = old_output


def output_as_string(func: Callable, *args: Any, **kwargs: Any) -> str:
    """
    Collect output printed by the given function as a string.
    """
    buffer = StringIO()
    with redirect_output(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def rprint(*args, **kwargs):
    """Print to global console, unless output stream is redirected."""

    stream = getattr(_output_context, "stream")
    if stream:
        rich.print(*args, **kwargs, file=stream)
    else:
        console.print(*args, **kwargs)


def output(message: str | Text = "", *args, text_wrap: Wrap = Wrap.WRAP, color=None):
    if isinstance(message, str):
        if color:
            rprint(Text(fill_text(message % args, text_wrap), color))
        else:
            rprint(fill_text(message % args, text_wrap))
    else:
        rprint(message)


def output_markdown(doc_str: str):
    output(fill_markdown(doc_str), text_wrap=Wrap.NONE)


def _output_message(
    message: str, *args, text_wrap: Wrap, color: str, transform: Callable[[str], str] = lambda x: x
):
    text = message % args if args else message
    rprint()
    rprint(Text(transform(fill_text(text, text_wrap)), color))
    rprint()


def output_separator():
    rprint(HRULE)


def output_status(message: str, *args, text_wrap: Wrap = Wrap.NONE):
    _output_message(message, *args, text_wrap=text_wrap, color=COLOR_OUTPUT)


def output_assistance(message: str, *args, text_wrap: Wrap = Wrap.NONE):
    _output_message(
        f"\n{EMOJI_ASSISTANT} " + message, *args, text_wrap=text_wrap, color=COLOR_ASSISTANCE
    )


def output_response(message: str = "", *args, text_wrap: Wrap = Wrap.NONE):
    _output_message(message, *args, text_wrap=text_wrap, color=COLOR_RESPONSE)


def output_heading(message: str, *args, text_wrap: Wrap = Wrap.NONE):
    _output_message(message, *args, text_wrap=text_wrap, color=COLOR_HEADING, transform=str.upper)
