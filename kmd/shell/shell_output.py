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
import rich.style
from rich.console import Group
from rich.markdown import Markdown
from rich.text import Text

from kmd.config.logger import get_console, get_logger
from kmd.config.text_styles import (
    BOX_BOTTOM,
    BOX_PREFIX,
    BOX_TOP,
    COLOR_ASSISTANCE,
    COLOR_FAILURE,
    COLOR_HEADING,
    COLOR_HELP,
    COLOR_HINT,
    COLOR_KEY,
    COLOR_RESPONSE,
    COLOR_SELECTION,
    COLOR_STATUS,
    COLOR_SUCCESS,
    CONSOLE_WRAP_WIDTH,
    emoji_bool,
    HRULE,
    MID_CORNER,
    VRULE_CHAR,
)
from kmd.shell.rich_indent import Indent
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
) -> str:
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
                    empty_indent=empty_indent,
                    replace_whitespace=replace_whitespace,
                )
            )

        para_sep = f"\n{empty_indent}\n"
        return para_sep.join(wrapped_paragraphs)


def format_name_and_description(
    name: str | Text,
    doc: str | Text,
    extra_note: Optional[str] = None,
    text_wrap: Wrap = Wrap.WRAP_INDENT,
) -> Text:
    def do_fill(text: str) -> str:
        return fill_text(textwrap.dedent(text).strip(), text_wrap=text_wrap)

    if isinstance(doc, Text):
        doc.plain = do_fill(doc.plain)
    else:
        doc = do_fill(doc)

    if isinstance(name, str):
        name = Text(name, style=COLOR_KEY)

    return Text.assemble(
        name,
        ((" " + extra_note, COLOR_HINT) if extra_note else ""),
        (": ", COLOR_HINT),
        "\n",
        doc,
    )


def format_paragraphs(*paragraphs: str | Text) -> Text:
    text: List[str | Text] = []
    for paragraph in paragraphs:
        if text:
            text.append("\n\n")
        text.append(paragraph)

    return Text.assemble(*text)


def format_success_or_failure(
    value: bool, true_str: str | Text = "", false_str: str | Text = ""
) -> Text:
    emoji = Text(emoji_bool(value), style=COLOR_SUCCESS if value else COLOR_FAILURE)
    if true_str or false_str:
        return Text.assemble(emoji, " ", true_str if value else false_str)
    else:
        return emoji


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
    INDENT = auto()
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
    if style == Style.INDENT:
        original_prefix = get_cprint_prefix()
        set_cprint_prefix(DEFAULT_INDENT)
        try:
            yield
        finally:
            _thread_local.output_prefix = original_prefix
    elif style == Style.BOX:
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


null_style = rich.style.Style.null()


def rprint(
    *args: str | Text | Markdown,
    width: Optional[int] = None,
    indent: str = "",
    raw: bool = False,
    **kwargs,
):
    """
    Print to global console, unless output stream is redirected.

    With `raw` True, we bypass rich formatting entirely.
    """

    global console
    stream = getattr(_output_context, "stream", None)

    if raw:
        # TODO: Indent not supported in raw mode.
        text = " ".join(str(arg) for arg in args)
        end = kwargs.get("end", "\n")
        if stream:
            stream.write(text)
            stream.write(end)
            stream.flush()
        else:
            console._write_buffer()  # Flush any pending rich content first.
            console.file.write(text)
            console.file.write(end)
            console.file.flush()
    else:
        if len(args) == 0:
            renderable = ""
        elif len(args) == 1:
            renderable = args[0]
        else:
            renderable = Group(*args)

        if indent:
            renderable = Indent(renderable, indent=indent)

        if stream:
            rich.print(renderable, **kwargs, file=stream)
        else:
            console.print(renderable, width=width, **kwargs)


def cprint(
    message: str | Text | Markdown = "",
    *args,
    text_wrap: Wrap = Wrap.WRAP,
    color=None,
    transform: Callable[[str], str] = lambda x: x,
    extra_indent: str = "",
    end="\n",
    width: Optional[int] = None,
    raw: bool = False,
):
    """
    Main way to print to the shell. Wraps `rprint` with all our formatting options.
    """
    empty_indent = extra_indent.strip()

    tl_prefix = get_cprint_prefix()
    if tl_prefix:
        extra_indent = tl_prefix + extra_indent

    if text_wrap.should_wrap and not width:
        width = CONSOLE_WRAP_WIDTH

    if not isinstance(message, (Text, Markdown)):
        message = str(message)

    if message:
        if isinstance(message, str):
            color = color or null_style
            text = message % args if args else message
            if text:
                filled_text = fill_text(
                    transform(text),
                    text_wrap,
                    extra_indent=extra_indent,
                    empty_indent=empty_indent,
                )
                rprint(
                    Text(filled_text, color),
                    end=end,
                    width=width,
                    raw=raw,
                )
            elif extra_indent:
                rprint(Text(extra_indent, style=null_style), end=end, raw=raw)
        else:
            rprint(message, end=end, width=width, indent=extra_indent)
    else:
        rprint(Text(empty_indent, style=null_style))


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
    format: str = "",
    extra_indent: str = "",
):
    markdown = Markdown(f"```{format}\n{message}\n```")
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
