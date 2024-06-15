"""
Output methods. These are for user interaction, not logging.
"""

from enum import Enum
import textwrap
from rich import print as rprint
from rich.text import Text
from kmd.config.text_styles import (
    COLOR_HEADING,
    COLOR_HINT,
    COLOR_KEY,
    COLOR_OUTPUT,
    COLOR_PLAIN,
    KMD_WRAP_WIDTH,
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
                        width=KMD_WRAP_WIDTH,
                        replace_whitespace=False,
                    )
                )
            elif text_wrap == Wrap.WRAP_FULL:
                wrapped_paragraphs.append(
                    textwrap.fill(
                        paragraph,
                        width=KMD_WRAP_WIDTH,
                        replace_whitespace=True,
                    )
                )
            elif text_wrap == Wrap.INDENTED:
                wrapped_paragraphs.append(
                    textwrap.fill(
                        paragraph,
                        width=KMD_WRAP_WIDTH - 4,
                        initial_indent="    ",
                        subsequent_indent="    ",
                        replace_whitespace=True,
                    )
                )
            elif text_wrap == Wrap.HANGING_INDENT:
                wrapped_paragraphs.append(
                    textwrap.fill(
                        paragraph,
                        width=KMD_WRAP_WIDTH - 8,
                        initial_indent="",
                        subsequent_indent="    ",
                        replace_whitespace=True,
                    )
                )

        return "\n\n".join(wrapped_paragraphs)
    else:
        raise ValueError(f"Unknown text_wrap value: {text_wrap}")


def output(message: str | Text = "", *args, text_wrap: Wrap = Wrap.WRAP, color=None):
    if type(message) == str:
        if color:
            rprint(Text(fill_text(message % args, text_wrap), color))
        else:
            rprint(fill_text(message % args, text_wrap))
    else:
        rprint(message)


def output_status(message: str, *args, text_wrap: Wrap = Wrap.NONE):
    rprint()
    rprint(Text(fill_text(message % args, text_wrap), COLOR_OUTPUT))


def output_heading(message: str, *args, text_wrap: Wrap = Wrap.NONE):
    rprint()
    rprint(Text(fill_text(message % args, text_wrap).upper(), COLOR_HEADING))
    rprint()


def format_docstr(name: str, doc: str) -> Text:
    doc = textwrap.dedent(doc).strip()
    wrapped = fill_text(doc, text_wrap=Wrap.INDENTED)
    return Text.assemble((name, COLOR_KEY), (": ", COLOR_HINT), "\n", (wrapped, COLOR_PLAIN))
