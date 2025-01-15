"""
Output to the shell UI. These are for user interaction, not logging.
"""

import textwrap
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from enum import auto, Enum
from typing import Callable, List, Optional

import rich
import rich.style
from rich.console import Group, OverflowMethod, RenderableType
from rich.text import Text

from kmd.config.logger import get_console, get_logger
from kmd.config.text_styles import (
    BOX_BOTTOM,
    BOX_PREFIX,
    BOX_TOP,
    COLOR_FAILURE,
    COLOR_HELP,
    COLOR_HINT,
    COLOR_RESPONSE,
    COLOR_STATUS,
    COLOR_SUCCESS,
    CONSOLE_WRAP_WIDTH,
    emoji_bool,
    HRULE,
    MID_CORNER,
    STYLE_ASSISTANCE,
    STYLE_HEADING,
    STYLE_KEY,
    VRULE_CHAR,
)
from kmd.shell_ui.rich_indent import Indent

from kmd.shell_ui.rich_markdown_custom import Markdown
from kmd.shell_ui.rich_markdown_kyrm import KyrmMarkdown
from kmd.text_wrap.text_styling import DEFAULT_INDENT, fill_text, Wrap

console = get_console()


def fill_rich_text(
    doc: str | Text, text_wrap: Wrap = Wrap.WRAP_INDENT, initial_column: int = 0
) -> str | Text:
    def do_fill(text: str) -> str:
        return fill_text(
            textwrap.dedent(text).strip(), text_wrap=text_wrap, initial_column=initial_column
        )

    if isinstance(doc, Text):
        doc.plain = do_fill(doc.plain)
    else:
        doc = do_fill(doc)

    return doc


def format_name_and_value(
    name: str | Text,
    doc: str | Text,
    text_wrap: Wrap = Wrap.WRAP_INDENT,
) -> Text:
    if isinstance(name, str):
        name = Text(name, style=STYLE_KEY)
    doc = fill_rich_text(doc, text_wrap=text_wrap, initial_column=len(name) + 2)

    return Text.assemble(name, (": ", COLOR_HINT), doc)


def format_name_and_description(
    name: str | Text,
    doc: str | Text,
    extra_note: Optional[str] = None,
    text_wrap: Wrap = Wrap.WRAP_INDENT,
) -> Text:
    if isinstance(name, str):
        name = Text(name, style=STYLE_KEY)
    doc = fill_rich_text(doc, text_wrap=text_wrap)

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
    value: bool, true_str: str | Text = "", false_str: str | Text = "", space: str = ""
) -> Text:
    """
    Format a success or failure message with an emoji followed by the true or false string.
    If false_str is not provided, it will be the same as true_str.
    """
    emoji = Text(emoji_bool(value), style=COLOR_SUCCESS if value else COLOR_FAILURE)
    if true_str or false_str:
        return Text.assemble(emoji, space, true_str if value else (false_str or true_str))
    else:
        return emoji


@dataclass
class TlPrintContext(threading.local):
    prefix: str = ""


_tl_print_context = TlPrintContext()
"""
Thread-local print settings.
"""


class Style(Enum):
    INDENT = auto()
    BOX = auto()
    PAD = auto()
    PAD_TOP = auto()


@contextmanager
def print_style(style: Style, color: Optional[str] = None):
    """
    Unified context manager for print styles.
    """
    if style == Style.INDENT:
        original_prefix = _tl_print_context.prefix
        _tl_print_context.prefix = DEFAULT_INDENT
        try:
            yield
        finally:
            _tl_print_context.prefix = original_prefix
    elif style == Style.BOX:
        cprint(BOX_TOP, color=color)
        original_prefix = _tl_print_context.prefix
        _tl_print_context.prefix = BOX_PREFIX
        try:
            yield
        finally:
            _tl_print_context.prefix = original_prefix
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
def console_pager(use_pager: bool = True):
    """
    Use a Rich pager, if requested and applicable. Otherwise does nothing.
    """
    console = get_console()
    if console.is_interactive and use_pager:
        with console.pager(styles=True):
            yield
    else:
        yield


null_style = rich.style.Style.null()


def rich_print(
    *args: RenderableType,
    width: Optional[int] = None,
    soft_wrap: Optional[bool] = None,
    indent: str = "",
    raw: bool = False,
    overflow: Optional[OverflowMethod] = "fold",
    **kwargs,
):
    """
    Print to the Rich console, either the global console or a thread-local
    override, if one is active. With `raw` true, we bypass rich formatting
    entirely and simply write to the console stream.
    """
    console = get_console()
    if raw:
        # TODO: Indent not supported in raw mode.
        text = " ".join(str(arg) for arg in args)
        end = kwargs.get("end", "\n")

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

        console.print(renderable, width=width, soft_wrap=soft_wrap, overflow=overflow, **kwargs)


def cprint(
    message: RenderableType = "",
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
    Main way to print to the shell. Wraps `rprint` with our additional
    formatting options for text fill and prefix.
    """
    empty_indent = extra_indent.strip()

    tl_prefix = _tl_print_context.prefix
    if tl_prefix:
        extra_indent = tl_prefix + extra_indent

    if text_wrap.should_wrap and not width:
        width = CONSOLE_WRAP_WIDTH

    # Handle unexpected types gracefully.
    if not isinstance(message, (Text, Markdown, RenderableType)):
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
                rich_print(
                    Text(filled_text, color),
                    end=end,
                    raw=raw,
                    width=width,
                )
            elif extra_indent:
                rich_print(
                    Text(extra_indent, style=null_style),
                    end=end,
                    raw=raw,
                    width=width,
                )
        else:
            rich_print(
                message,
                end=end,
                indent=extra_indent,
                width=width,
            )
    else:
        # Blank line.
        rich_print(Text(empty_indent, style=null_style))


log = get_logger(__name__)


def print_markdown(doc_str: str, extra_indent: str = "", enable_markdown: bool = True):
    doc_str = str(doc_str)  # Convenience for lazy objects.

    if enable_markdown:
        doc = KyrmMarkdown(doc_str, justify="left")
    else:
        doc = doc_str

    cprint(doc, extra_indent=extra_indent)


def print_hrule(color: Optional[str] = None):
    """
    Print a horizontal rule.
    """
    rule = HRULE
    tl_prefix = _tl_print_context.prefix
    if tl_prefix:
        if tl_prefix.startswith(VRULE_CHAR):
            rule = MID_CORNER + rule[len(VRULE_CHAR) :]
        else:
            rule = tl_prefix + rule[len(tl_prefix) :]
    rich_print(rule, style=color)


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


def print_assistance(
    message: str | Text | Markdown, *args, text_wrap: Wrap = Wrap.NONE, extra_indent: str = ""
):
    cprint(
        message,
        *args,
        text_wrap=text_wrap,
        color=STYLE_ASSISTANCE,
        extra_indent=extra_indent,
        width=CONSOLE_WRAP_WIDTH,
    )


def print_code_block(
    message: str,
    *args,
    format: str = "",
    extra_indent: str = "",
):
    markdown = KyrmMarkdown(f"```{format}\n{message}\n```")
    cprint(markdown, *args, text_wrap=Wrap.NONE, extra_indent=extra_indent)


def print_text_block(message: str | Text | Markdown, *args, extra_indent: str = ""):
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
    color: str = STYLE_HEADING,
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
    color: str = STYLE_HEADING,
):
    with print_style(Style.PAD_TOP):
        cprint(message, *args, text_wrap=text_wrap, color=color, extra_indent=extra_indent)
