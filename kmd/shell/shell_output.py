"""
Output to the shell UI. These are for user interaction, not logging.
"""

import sys
import textwrap
import threading
from contextlib import contextmanager
from enum import auto, Enum
from io import StringIO
from typing import Any, Callable, List, Optional

import rich
from rich.markdown import Markdown
from rich.text import Text

from kmd.config.logger import get_console, get_logger
from kmd.config.text_styles import (
    BOX_BOTTOM,
    BOX_PREFIX,
    BOX_TOP,
    COLOR_ASSISTANCE,
    COLOR_HEADING,
    COLOR_HELP,
    COLOR_HINT,
    COLOR_KEY,
    COLOR_RESPONSE,
    COLOR_SELECTION,
    COLOR_STATUS,
    CONSOLE_WRAP_WIDTH,
    HRULE,
    MID_CORNER,
    VRULE_CHAR,
)
from kmd.text_formatting.markdown_normalization import DEFAULT_WRAP_WIDTH
from kmd.text_formatting.text_wrapping import wrap_paragraph
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

    @property
    def should_wrap(self) -> bool:
        return self in [Wrap.WRAP, Wrap.WRAP_FULL, Wrap.WRAP_INDENT, Wrap.HANGING_INDENT]


def fill_text(
    text: str, text_wrap=Wrap.WRAP, extra_indent: str = "", empty_indent: str = ""
) -> str:
    if text_wrap in [Wrap.NONE, Wrap.INDENT_ONLY]:
        indent = extra_indent + DEFAULT_INDENT if text_wrap == Wrap.INDENT_ONLY else extra_indent
        lines = text.splitlines()
        if lines:
            return "\n".join(indent + line for line in lines)
        else:
            return empty_indent
    elif text_wrap in [Wrap.WRAP, Wrap.WRAP_FULL, Wrap.WRAP_INDENT, Wrap.HANGING_INDENT]:
        paragraphs = split_paragraphs(text)
        wrapped_paragraphs = []

        for i, paragraph in enumerate(paragraphs):
            if text_wrap == Wrap.WRAP:
                wrapped_paragraphs.append(
                    wrap_paragraph(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH,
                        initial_indent=extra_indent,
                        subsequent_indent=extra_indent,
                        empty_indent=extra_indent.strip(),
                        replace_whitespace=False,
                    )
                )
            elif text_wrap == Wrap.WRAP_FULL:
                wrapped_paragraphs.append(
                    wrap_paragraph(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH,
                        initial_indent=extra_indent,
                        subsequent_indent=extra_indent,
                        empty_indent=extra_indent.strip(),
                        replace_whitespace=True,
                    )
                )
            elif text_wrap == Wrap.WRAP_INDENT:
                wrapped_paragraphs.append(
                    wrap_paragraph(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH - len(extra_indent + DEFAULT_INDENT),
                        initial_indent=extra_indent + DEFAULT_INDENT,
                        subsequent_indent=extra_indent + DEFAULT_INDENT,
                        empty_indent=extra_indent.strip(),
                        replace_whitespace=True,
                    )
                )
            elif text_wrap == Wrap.HANGING_INDENT:
                wrapped_paragraphs.append(
                    wrap_paragraph(
                        paragraph,
                        width=CONSOLE_WRAP_WIDTH - len(extra_indent + DEFAULT_INDENT),
                        # Hang the first line of the first paragraph. All other paragraphs are indented.
                        initial_indent=extra_indent + DEFAULT_INDENT if i > 0 else extra_indent,
                        subsequent_indent=extra_indent + DEFAULT_INDENT,
                        empty_indent=extra_indent.strip(),
                        replace_whitespace=True,
                    )
                )
        para_sep = f"\n{empty_indent}\n"
        return para_sep.join(wrapped_paragraphs)
    else:
        raise ValueError(f"Unknown text_wrap value: {text_wrap}")


def format_name_and_description(
    name: str, doc: str, extra_note: Optional[str] = None, text_wrap: Wrap = Wrap.WRAP_INDENT
) -> Text:
    doc = textwrap.dedent(doc).strip()
    wrapped_doc = fill_text(doc, text_wrap=text_wrap)
    return Text.assemble(
        ("`", COLOR_HINT),
        (name, COLOR_KEY),
        ("`", COLOR_HINT),
        ((" " + extra_note, COLOR_HINT) if extra_note else ""),
        (": ", COLOR_HINT),
        "\n",
        wrapped_doc,
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
_output_context.rich_console = True


@contextmanager
def redirect_output(new_output):
    old_output = getattr(_output_context, "stream", sys.stdout)
    _output_context.stream = new_output
    _output_context.rich_console = False
    try:
        yield
    finally:
        _output_context.stream = old_output
        _output_context.rich_console = True


_thread_local = threading.local()


def get_cprint_prefix() -> str:
    if not hasattr(_thread_local, "output_prefix"):
        _thread_local.output_prefix = ""

    return _thread_local.output_prefix


def set_cprint_prefix(prefix: str):
    _thread_local.output_prefix = prefix


class Style(Enum):
    BOX = auto()
    PAD = auto()
    PAD_TOP = auto()


@contextmanager
def print_style(style: Style, color: Optional[str] = None):
    """
    Unified context manager for print styles.

    Args:
        style: Style enum indicating the desired style (BOX or PAD)
        color: Optional color for box style
    """
    if style == Style.BOX:
        cprint(BOX_TOP, color=color)
        original_prefix = get_cprint_prefix()
        set_cprint_prefix(BOX_PREFIX)
        try:
            yield
        finally:
            _thread_local.output_prefix = original_prefix
            cprint(BOX_BOTTOM, color=color)
    elif style == Style.PAD:
        cprint()
        yield
        cprint()
    elif style == Style.PAD_TOP:
        cprint()
        yield
    else:
        raise ValueError(f"Unknown style: {style}")


@contextmanager
def console_pager(use_pager: Optional[bool] = None):
    """
    Use Rich pager if requested, or detect if it's applicable.
    """
    if _output_context.rich_console and use_pager is not False:
        with get_console().pager(styles=True):
            yield
    else:
        yield


def output_as_string(func: Callable, *args: Any, **kwargs: Any) -> str:
    """
    Collect output printed by the given function as a string.
    """
    buffer = StringIO()
    with redirect_output(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def rprint(*args, width: Optional[int] = None, **kwargs):
    """Print to global console, unless output stream is redirected."""

    stream = getattr(_output_context, "stream", None)
    if stream:
        rich.print(*args, **kwargs, file=stream)
    else:
        global console
        console.print(*args, width=width, **kwargs)


def cprint(
    message: str | Text | Markdown = "",
    *args,
    text_wrap: Wrap = Wrap.WRAP,
    color=None,
    transform: Callable[[str], str] = lambda x: x,
    extra_indent: str = "",
    end="\n",
    width: Optional[int] = None,
):
    """
    Main way to print to the shell. Wraps `rprint` with all our formatting options.
    """
    empty_indent = extra_indent.strip()

    tl_prefix = get_cprint_prefix()
    if tl_prefix:
        extra_indent = tl_prefix + extra_indent

    if text_wrap.should_wrap and not width:
        width = DEFAULT_WRAP_WIDTH

    if not isinstance(message, (Text, Markdown)):
        message = str(message)

    if message:
        if isinstance(message, str):
            text = message % args if args else message
            if text:
                filled_text = fill_text(
                    transform(text),
                    text_wrap,
                    extra_indent=extra_indent,
                    empty_indent=empty_indent,
                )
                rprint(Text(filled_text, color) if color else filled_text, end=end, width=width)
            elif extra_indent:
                rprint(extra_indent, end=end)
        else:
            rprint(extra_indent, end="")
            rprint(message, end=end, width=width)
    else:
        rprint(empty_indent)


log = get_logger(__name__)


def print_markdown(doc_str: str, extra_indent: str = "", rich_markdown_display: bool = True):
    doc_str = str(doc_str)  # Convenience for lazy objects.
    if rich_markdown_display and _output_context.rich_console:
        doc = Markdown(doc_str, justify="left")
    else:
        doc = doc_str

    cprint(doc, extra_indent=extra_indent)


def print_hrule(color: Optional[str] = None):
    """
    Print a horizontal rule.
    """
    rule = HRULE
    tl_prefix = get_cprint_prefix()
    if tl_prefix:
        if tl_prefix.startswith(VRULE_CHAR):
            rule = MID_CORNER + rule[len(VRULE_CHAR) :]
        else:
            rule = tl_prefix + rule[len(tl_prefix) :]
    rprint(rule, style=color)


def print_selection(
    message: str,
    *args,
    text_wrap: Wrap = Wrap.NONE,
    extra_indent: str = "",
):
    cprint(
        message,
        *args,
        text_wrap=text_wrap,
        color=COLOR_SELECTION,
        extra_indent=extra_indent,
    )


def print_status(
    message: str,
    *args,
    text_wrap: Wrap = Wrap.NONE,
    extra_indent: str = "",
):
    with print_style(Style.PAD):
        cprint(
            message,
            *args,
            text_wrap=text_wrap,
            color=COLOR_STATUS,
            extra_indent=extra_indent,
        )


def print_result(
    message: str,
    *args,
    text_wrap: Wrap = Wrap.NONE,
    extra_indent: str = "",
):
    cprint(
        message,
        *args,
        text_wrap=text_wrap,
        extra_indent=extra_indent,
    )


def print_help(message: str, *args, text_wrap: Wrap = Wrap.WRAP, extra_indent: str = ""):
    cprint(message, *args, text_wrap=text_wrap, color=COLOR_HELP, extra_indent=extra_indent)


def print_assistance(message: str, *args, text_wrap: Wrap = Wrap.NONE, extra_indent: str = ""):
    cprint(
        message,
        *args,
        text_wrap=text_wrap,
        color=COLOR_ASSISTANCE,
        extra_indent=extra_indent,
        width=CONSOLE_WRAP_WIDTH,
    )


def print_code_block(
    message: str,
    *args,
    format_name="",
    extra_indent: str = "",
):
    markdown = Markdown(f"```{format_name}\n{message}\n```")
    cprint(markdown, *args, text_wrap=Wrap.NONE, extra_indent=extra_indent)


def print_text_block(message: str, *args, extra_indent: str = ""):
    cprint(message, text_wrap=Wrap.WRAP_FULL, *args, extra_indent=extra_indent)


def print_response(message: str = "", *args, text_wrap: Wrap = Wrap.NONE, extra_indent: str = ""):
    with print_style(Style.PAD):
        cprint(
            message,
            *args,
            text_wrap=text_wrap,
            color=COLOR_RESPONSE,
            extra_indent=extra_indent,
        )


def print_heading(
    message: str,
    *args,
    text_wrap: Wrap = Wrap.NONE,
    extra_indent: str = "",
    color: str = COLOR_HEADING,
):
    with print_style(Style.PAD):
        cprint(
            Markdown(f"## {message.upper()}"),
            *args,
            text_wrap=text_wrap,
            color=color,
            extra_indent=extra_indent,
            width=CONSOLE_WRAP_WIDTH,
        )


def print_small_heading(
    message: str,
    *args,
    text_wrap: Wrap = Wrap.NONE,
    extra_indent: str = "",
    color: str = COLOR_HEADING,
):
    with print_style(Style.PAD_TOP):
        cprint(message, *args, text_wrap=text_wrap, color=color, extra_indent=extra_indent)
