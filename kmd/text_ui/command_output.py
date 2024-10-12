"""
Output methods. These are for user interaction, not logging.
"""

import sys
import textwrap
import threading
from contextlib import contextmanager
from enum import Enum
from io import StringIO
from textwrap import dedent, indent
from typing import Any, Callable, List, Optional

import rich
from rich.markdown import Markdown
from rich.text import Text

from kmd.config.logger import get_console
from kmd.config.text_styles import (
    COLOR_ASSISTANCE,
    COLOR_HEADING,
    COLOR_HELP,
    COLOR_HINT,
    COLOR_KEY,
    COLOR_RESPONSE,
    COLOR_RESULT,
    COLOR_STATUS,
    CONSOLE_WRAP_WIDTH,
    EMOJI_ASSISTANT,
    HRULE,
)
from kmd.text_formatting.markdown_normalization import normalize_markdown, wrap_lines_to_width
from kmd.text_formatting.text_wrapping import text_wrap_fill
from kmd.util.format_utils import DEFAULT_INDENT, split_paragraphs

console = get_console()


class Wrap(Enum):
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


def fill_text(text: str, text_wrap=Wrap.WRAP, extra_indent: str = "") -> str:
    if text_wrap == Wrap.NONE:
        return text
    elif text_wrap == Wrap.INDENT_ONLY:
        return indent(text, prefix="    ")
    elif text_wrap in [Wrap.WRAP, Wrap.WRAP_FULL, Wrap.WRAP_INDENT, Wrap.HANGING_INDENT]:
        paragraphs = split_paragraphs(text)
        wrapped_paragraphs = []

        for i, paragraph in enumerate(paragraphs):
            if text_wrap == Wrap.WRAP:
                wrapped_paragraphs.append(
                    text_wrap_fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH,
                        initial_indent=extra_indent,
                        subsequent_indent=extra_indent,
                        replace_whitespace=False,
                    )
                )
            elif text_wrap == Wrap.WRAP_FULL:
                wrapped_paragraphs.append(
                    text_wrap_fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH,
                        initial_indent=extra_indent,
                        subsequent_indent=extra_indent,
                        replace_whitespace=True,
                    )
                )
            elif text_wrap == Wrap.WRAP_INDENT:
                wrapped_paragraphs.append(
                    text_wrap_fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH - len(extra_indent + DEFAULT_INDENT),
                        initial_indent=extra_indent + DEFAULT_INDENT,
                        subsequent_indent=extra_indent + DEFAULT_INDENT,
                        replace_whitespace=True,
                    )
                )
            elif text_wrap == Wrap.HANGING_INDENT:
                wrapped_paragraphs.append(
                    text_wrap_fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH - len(extra_indent + DEFAULT_INDENT),
                        # Hang the first line of the first paragraph. All other paragraphs are indented.
                        initial_indent=extra_indent + DEFAULT_INDENT if i > 0 else extra_indent,
                        subsequent_indent=extra_indent + DEFAULT_INDENT,
                        replace_whitespace=True,
                    )
                )

        return "\n\n".join(wrapped_paragraphs)
    else:
        raise ValueError(f"Unknown text_wrap value: {text_wrap}")


def fill_markdown(doc_str: str):
    return normalize_markdown(dedent(doc_str).strip(), line_wrapper=wrap_lines_to_width)


def format_name_and_description(name: str, doc: str, extra_note: Optional[str] = None) -> Text:
    doc = textwrap.dedent(doc).strip()
    wrapped = fill_text(doc, text_wrap=Wrap.WRAP_INDENT)
    return Text.assemble(
        ("`", COLOR_HINT),
        (name, COLOR_KEY),
        ("`", COLOR_HINT),
        ((" " + extra_note, COLOR_HINT) if extra_note else ""),
        (": ", COLOR_HINT),
        "\n",
        wrapped,
    )


def format_paragraphs(*paragraphs: str | Text):
    text: List[str | Text] = []
    for paragraph in paragraphs:
        if text:
            text.append("\n\n")
        text.append(paragraph)

    return Text.assemble(*text)


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

    stream = getattr(_output_context, "stream", None)
    if stream:
        rich.print(*args, **kwargs, file=stream)
    else:
        console.print(*args, **kwargs)


def output(
    message: str | Text | Markdown = "",
    *args,
    text_wrap: Wrap = Wrap.WRAP,
    color=None,
    transform: Callable[[str], str] = lambda x: x,
    extra_indent: str = "",
    extra_newlines: bool = False,
    end="\n",
):
    if extra_newlines:
        rprint()
    if isinstance(message, str):
        text = message % args if args else message
        filled_text = fill_text(transform(text), text_wrap, extra_indent)
        rprint(Text(filled_text, color) if color else filled_text, end=end)
    else:
        rprint(extra_indent, end="")
        rprint(message, end=end)
    if extra_newlines:
        rprint()


def output_markdown(doc_str: str, extra_indent: str = "", use_rich_markdown: bool = True):
    doc = fill_markdown(doc_str)
    if use_rich_markdown:
        doc = Markdown(doc, justify="left")

    output(doc, text_wrap=Wrap.NONE, extra_indent=extra_indent)


def output_separator():
    rprint(HRULE)


def output_status(
    message: str,
    *args,
    text_wrap: Wrap = Wrap.NONE,
    extra_indent: str = "",
    extra_newlines: bool = True,
):
    output(
        message,
        *args,
        text_wrap=text_wrap,
        color=COLOR_STATUS,
        extra_indent=extra_indent,
        extra_newlines=extra_newlines,
    )


def output_result(
    message: str,
    *args,
    text_wrap: Wrap = Wrap.NONE,
    extra_indent: str = "",
    extra_newlines: bool = False,
):
    output(
        message,
        *args,
        text_wrap=text_wrap,
        color=COLOR_RESULT,
        extra_indent=extra_indent,
        extra_newlines=extra_newlines,
    )


def output_help(message: str, *args, text_wrap: Wrap = Wrap.NONE, extra_indent: str = ""):
    output(message, *args, text_wrap=text_wrap, color=COLOR_HELP, extra_indent=extra_indent)


def output_assistance(
    message: str, *args, model: str = "", text_wrap: Wrap = Wrap.NONE, extra_indent: str = ""
):
    model_str = f"({model})" if model else ""
    output(
        f"\n{EMOJI_ASSISTANT}{model_str} " + message,
        *args,
        text_wrap=text_wrap,
        color=COLOR_ASSISTANCE,
        extra_indent=extra_indent,
        extra_newlines=True,
    )


def output_response(message: str = "", *args, text_wrap: Wrap = Wrap.NONE, extra_indent: str = ""):
    output(
        message,
        *args,
        text_wrap=text_wrap,
        color=COLOR_RESPONSE,
        extra_indent=extra_indent,
        extra_newlines=True,
    )


def output_heading(message: str, *args, text_wrap: Wrap = Wrap.NONE, extra_indent: str = ""):
    output(
        Markdown(f"## {message.upper()}"),
        *args,
        text_wrap=text_wrap,
        color=COLOR_HEADING,
        extra_indent=extra_indent,
        extra_newlines=True,
    )
