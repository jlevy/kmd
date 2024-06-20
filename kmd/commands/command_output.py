"""
Output methods. These are for user interaction, not logging.
"""

from io import StringIO
import threading
import sys
from contextlib import contextmanager
from enum import Enum
import textwrap
from typing import Any, Callable
from rich import print as rprint
from rich.text import Text
from kmd.config.text_styles import (
    COLOR_ASSISTANCE,
    COLOR_HEADING,
    COLOR_HINT,
    COLOR_KEY,
    COLOR_OUTPUT,
    COLOR_PLAIN,
    CONSOLE_WRAP_WIDTH,
)


class Wrap(Enum):
    NONE = "none"
    WRAP = "wrap"
    WRAP_FULL = "wrap_full"
    INDENTED = "indented"
    HANGING_INDENT = "hanging_indent"


def fill_text(text: str, text_wrap=Wrap.WRAP) -> str:
    if text_wrap == Wrap.NONE:
        return text
    elif text_wrap in [Wrap.WRAP, Wrap.WRAP_FULL, Wrap.INDENTED, Wrap.HANGING_INDENT]:
        paragraphs = text.split("\n\n")
        wrapped_paragraphs = []

        for paragraph in paragraphs:
            if text_wrap == Wrap.WRAP:
                wrapped_paragraphs.append(
                    textwrap.fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH,
                        replace_whitespace=False,
                    )
                )
            elif text_wrap == Wrap.WRAP_FULL:
                wrapped_paragraphs.append(
                    textwrap.fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH,
                        replace_whitespace=True,
                    )
                )
            elif text_wrap == Wrap.INDENTED:
                wrapped_paragraphs.append(
                    textwrap.fill(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH - 4,
                        initial_indent="    ",
                        subsequent_indent="    ",
                        replace_whitespace=True,
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
                    )
                )

        return "\n\n".join(wrapped_paragraphs)
    else:
        raise ValueError(f"Unknown text_wrap value: {text_wrap}")


def format_action_description(name: str, doc: str) -> Text:
    doc = textwrap.dedent(doc).strip()
    wrapped = fill_text(doc, text_wrap=Wrap.INDENTED)
    return Text.assemble((name, COLOR_KEY), (": ", COLOR_HINT), "\n", (wrapped, COLOR_PLAIN))


# Allow output stream to be customized if desired.
_output_stream = threading.local()
_output_stream.current = sys.stdout


@contextmanager
def redirect_output(new_output):
    old_output = getattr(_output_stream, "current", sys.stdout)
    _output_stream.current = new_output
    try:
        yield
    finally:
        _output_stream.current = old_output


def output_as_string(func: Callable, *args: Any, **kwargs: Any) -> str:
    """
    Collect output printed by the given function as a string.
    """
    buffer = StringIO()
    with redirect_output(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def _current_output():
    return getattr(_output_stream, "current", sys.stdout)


def output(message: str | Text = "", *args, text_wrap: Wrap = Wrap.WRAP, color=None):
    out = _current_output()
    if type(message) == str:
        if color:
            rprint(Text(fill_text(message % args, text_wrap), color), file=out)
        else:
            rprint(fill_text(message % args, text_wrap), file=out)
    else:
        rprint(message, file=out)


def _output_message(
    message: str, *args, text_wrap: Wrap, color: str, transform: Callable[[str], str] = lambda x: x
):
    out = _current_output()
    rprint(file=out)
    rprint(Text(transform(fill_text(message % args, text_wrap)), color), file=out)
    rprint(file=out)


def output_status(message: str, *args, text_wrap: Wrap = Wrap.NONE):
    _output_message(message, *args, text_wrap=text_wrap, color=COLOR_OUTPUT)


def output_assistance(message: str, *args, text_wrap: Wrap = Wrap.NONE):
    _output_message("ASSISTANT:", *args, text_wrap=text_wrap, color=COLOR_HEADING)
    _output_message(message, *args, text_wrap=text_wrap, color=COLOR_ASSISTANCE)


def output_heading(message: str, *args, text_wrap: Wrap = Wrap.NONE):
    _output_message(message, *args, text_wrap=text_wrap, color=COLOR_HEADING, transform=str.upper)
