"""
Settings that define the visual appearance of text outputs.
"""

import re

from kmd.config import colors

## Settings

CONSOLE_WRAP_WIDTH = 80
"""Wrap width for console output."""

SPINNER = "dots12"
"""Progress spinner. For a list, use `python -m rich.spinner`."""

BAT_THEME = "Coldark-Dark"

BAT_STYLE = "header-filename,header-filesize,grid,changes"

## Text styles

LOGO = "⎪K⎪M⎪D⎪"


## Prompt colors

PROMPT_COLOR_NORMAL = "BOLD_GREEN"

PROMPT_COLOR_WARN = "INTENSE_YELLOW"

PROMPT_CHAT_COLOR = "#e0f2f5"

PROMPT_ASSISTANT_COLOR = "#c6d3fb"

PROMPT_INPUT_COLOR = colors.input


## Colors

COLOR_LOGO = "bold magenta"

COLOR_PLAIN = "default"

COLOR_HEADING = "bold bright_green"

COLOR_EMPH = "bright_green"

COLOR_EMPH_ALT = "bright_green"

COLOR_SELECTION = "bright_yellow"

COLOR_STATUS = "yellow"

COLOR_RESULT = "default"

COLOR_HELP = "bright_blue"

COLOR_ASSISTANCE = "italic bright_blue"

COLOR_RESPONSE = "bright_blue"

COLOR_SUGGESTION = "bright_blue"

COLOR_LITERAL = "bright_blue"

COLOR_KEY = "bright_blue"

COLOR_VALUE = "cyan"

COLOR_PATH = "cyan"

COLOR_HINT = "bright_black"

COLOR_SUCCESSS = "green"

COLOR_SKIP = "green"

COLOR_WARN = "bright_red"

COLOR_ERROR = "bright_red"

COLOR_TASK = "magenta"

COLOR_SAVED = "blue"

COLOR_TIMING = "blue"

COLOR_CALL = "bright_yellow"

COLOR_COMMAND_TEXT = "bold default"

COLOR_ACTION_TEXT = "bold default"

COLOR_SIZE1 = "bright_black"

COLOR_SIZE2 = "blue"

COLOR_SIZE3 = "cyan"

COLOR_SIZE4 = "bright_green"

COLOR_SIZE5 = "yellow"

COLOR_SIZE6 = "bright_red"


# Boxes

HRULE_CHAR = "─"
VRULE_CHAR = "│"

UL_CORNER = "┬"
MID_CORNER = "┼"
LL_CORNER = "┴"

BOX_TOP = UL_CORNER + HRULE_CHAR * (CONSOLE_WRAP_WIDTH - len(UL_CORNER))
BOX_MID = MID_CORNER + HRULE_CHAR * (CONSOLE_WRAP_WIDTH - len(MID_CORNER))
BOX_BOTTOM = LL_CORNER + HRULE_CHAR * (CONSOLE_WRAP_WIDTH - len(LL_CORNER))
BOX_PREFIX = VRULE_CHAR + " "


## Formatting

NBSP = "\u00a0"

# HRULE = ("⋯ " * (CONSOLE_WRAP_WIDTH // 2)).strip()
HRULE = HRULE_CHAR * CONSOLE_WRAP_WIDTH

HRULE_SHORT = ("⋯ " * 20).strip()

## Symbols

SYMBOL_SEP = "⎪"

SYMBOL_PARA = "¶"

SYMBOL_SENT = "S"


## Symbols and emojis

PROMPT_MAIN = "❯"

PROMPT_FORM = "❯❯"

PROMPT_ASSIST = "(assistant) ❯"

EMOJI_HINT = "👉"

EMOJI_TASK = "⛭"

EMOJI_WARN = "△"

EMOJI_ERROR = EMOJI_WARN + EMOJI_WARN

EMOJI_SAVED = "⩣"

EMOJI_TIMING = "⏱"

EMOJI_SUCCESS = "[✓]"

EMOJI_SKIP = "[−]"

EMOJI_FAILURE = "[✗]"

EMOJI_CALL_BEGIN = "≫"

EMOJI_CALL_END = "≪"

EMOJI_ASSISTANT = "🤖"

EMOJI_TRUE = "✓"

EMOJI_FALSE = "✗"

EMOJI_MSG_INDENT = "⋮"

EMOJI_BREADCRUMB_SEP = "›"


## Special headings

TASK_STACK_HEADER = "Task stack:"


## Rich setup

from rich.highlighter import _combine_regex, RegexHighlighter
from rich.style import Style

URL_CHARS = r"-0-9a-zA-Z$_+!`(),.?/;:&=%#~"

ITEM_ID_CHARS = URL_CHARS + r"@\[\]"


class KmdHighlighter(RegexHighlighter):
    """
    Highlighter based on the repr highlighter with additions.
    """

    base_style = "kmd."
    highlights = [
        _combine_regex(
            # Task stack in logs:
            f"(?P<task_stack_header>{re.escape(TASK_STACK_HEADER)})",
            f"(?P<task_stack>{re.escape(EMOJI_TASK)}.*)",
            f"(?P<task_stack_prefix>{re.escape(EMOJI_MSG_INDENT)})",
            # Emoji colors:
            f"(?P<task>{re.escape(EMOJI_TASK)})",
            f"(?P<success>{re.escape(EMOJI_SUCCESS)})",
            f"(?P<skip>{re.escape(EMOJI_SKIP)})",
            f"(?P<failure>{re.escape(EMOJI_FAILURE)})",
            f"(?P<timing>{re.escape(EMOJI_TIMING)})",
            f"(?P<warn>{re.escape(EMOJI_WARN)})",
            f"(?P<saved>{re.escape(EMOJI_SAVED)})",
            f"(?P<log_call>{re.escape(EMOJI_CALL_BEGIN)}|{re.escape(EMOJI_CALL_END)})",
            f"(?P<box_chars>{HRULE_CHAR}|{VRULE_CHAR}|{UL_CORNER}|{LL_CORNER})",
        ),
        _combine_regex(
            # Quantities and times:
            r"\b(?P<age_sec>[0-9.,]+ ?(s|sec) ago)\b",
            r"\b(?P<age_min>[0-9.,]+ ?(m|min) ago)\b",
            r"\b(?P<age_hr>[0-9.,]+ ?(?:h|hr|hrs|hour|hours) ago)\b",
            r"\b(?P<age_day>[0-9.,]+ ?(?:d|day|days) ago)\b",
            r"\b(?P<age_week>[0-9.,]+ ?(?:w|week|weeks) ago)\b",
            r"\b(?P<age_year>[0-9.,]+ ?(?:y|year|years) ago)\b",
            r"\b(?P<size_b>(?<!\w)[0-9.,]+ ?(B|Bytes|bytes))\b",
            r"\b(?P<size_k>(?<!\w)[0-9.,]+ ?(K|KB|kb))\b",
            r"\b(?P<size_m>(?<!\w)[0-9.,]+ ?(M|MB|mb)\b)",
            r"\b(?P<size_gtp>(?<!\w)[0-9.,]+ ?(G|GB|gb|T|TB|tb|P|PB|pb))\b",
            r"\b(?P<part_count>\w+ \d+ of \d+(?!\-\w))\b",
            r"\b(?P<duration>(?<!\w)\-?[0-9]+\.?[0-9]*(ms|s)\b(?!\-\w))\b",
        ),
        _combine_regex(
            rf"\b(?P<item_id_prefix>id:\w+:[{ITEM_ID_CHARS}]+)",
            r"(?P<tag_start><)(?P<tag_name>[-\w.:|]*)(?P<tag_contents>[\w\W]*)(?P<tag_end>>)",
            r'(?P<attrib_name>[\w_-]{1,50})=(?P<attrib_value>"?[\w_]+"?)?',
            r"(?P<brace>[][{}()])",
        ),
        _combine_regex(
            r"(?P<ellipsis>(\.\.\.|…))",
            r"(?P<at_mention>(?<!\w)@(?=\w))",  # @some/file.txt
            # A subset of the repr-style highlights:
            r"(?P<ipv4>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            r"(?P<uuid>[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
            r"(?P<call>[\w.]*?)\(",
            r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
            # r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b(?!\-\w)|0x[0-9a-fA-F]*)",
            r"(?P<path>\B(/[-\w._+]+)*\/)(?P<filename>[-\w._+]*)?",
            # r"(?P<relpath>\B([\w._+][-\w._+]*)*(/\w[-\w._+]*)+)*\.(html|htm|pdf|yaml|yml|md|txt)",
            r"(?<![\\\w])(?P<str>b?'''.*?(?<!\\)'''|b?'.*?(?<!\\)'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
            rf"(?P<url>(file|https|http|ws|wss)://[{URL_CHARS}]*)",
            r"(?P<code_span>`[^`\n]+`)",
        ),
    ]


RICH_STYLES = {
    "markdown.h1": Style(color=COLOR_EMPH, bold=True),
    "markdown.h2": Style(color=COLOR_EMPH, bold=True),
    "markdown.h3": Style(color=COLOR_EMPH, bold=True, italic=True),
    "markdown.h4": Style(color=COLOR_EMPH_ALT, bold=True),
    "kmd.ellipsis": Style(color=COLOR_HINT),
    "kmd.at_mention": Style(color=COLOR_HINT, bold=True),
    "kmd.indent": Style(color=COLOR_KEY, dim=True),
    "kmd.error": Style(color=COLOR_ERROR, bold=True),
    "kmd.str": Style(color=COLOR_LITERAL, italic=False, bold=False),
    "kmd.brace": Style(bold=True),
    "kmd.comma": Style(bold=True),
    "kmd.ipv4": Style(color=COLOR_KEY),
    "kmd.ipv6": Style(color=COLOR_KEY),
    "kmd.eui48": Style(color=COLOR_KEY),
    "kmd.eui64": Style(color=COLOR_KEY),
    "kmd.tag_start": Style(),
    "kmd.tag_name": Style(color=COLOR_VALUE),
    "kmd.tag_contents": Style(color="default"),
    "kmd.tag_end": Style(),
    "kmd.attrib_name": Style(color=COLOR_KEY, italic=False),
    "kmd.attrib_equal": Style(),
    "kmd.attrib_value": Style(color=COLOR_VALUE, italic=False),
    # "kmd.number": Style(color=COLOR_KEY, italic=False),
    "kmd.duration": Style(color=COLOR_KEY, italic=False),
    "kmd.item_id_prefix": Style(color=COLOR_HINT, italic=False),
    "kmd.part_count": Style(italic=True),
    "kmd.time_ago": Style(color=COLOR_KEY, italic=False),
    "kmd.file_size": Style(color=COLOR_VALUE, italic=False),
    "kmd.code_span": Style(color=COLOR_VALUE, italic=False),
    # "kmd.number_complex": Style(color=COLOR_KEY, italic=False),  # same
    "kmd.bool_true": Style(color=COLOR_VALUE, italic=True),
    "kmd.bool_false": Style(color=COLOR_VALUE, italic=True),
    "kmd.none": Style(color=COLOR_VALUE, italic=True),
    "kmd.url": Style(underline=True, color=COLOR_VALUE, italic=False, bold=False),
    "kmd.uuid": Style(color=COLOR_LITERAL, bold=False),
    "kmd.call": Style(italic=True),
    "kmd.path": Style(color=COLOR_PATH),
    "kmd.age_sec": Style(color=COLOR_SIZE6),
    "kmd.age_min": Style(color=COLOR_SIZE5),
    "kmd.age_hr": Style(color=COLOR_SIZE4),
    "kmd.age_day": Style(color=COLOR_SIZE3),
    "kmd.age_week": Style(color=COLOR_SIZE2),
    "kmd.age_year": Style(color=COLOR_SIZE1),
    "kmd.size_b": Style(color=COLOR_SIZE1),
    "kmd.size_k": Style(color=COLOR_SIZE2),
    "kmd.size_m": Style(color=COLOR_SIZE3),
    "kmd.size_gtp": Style(color=COLOR_SIZE4),
    "kmd.filename": Style(color=COLOR_VALUE),
    "kmd.task_stack_header": Style(color=COLOR_TASK, italic=True),
    "kmd.task_stack": Style(color=COLOR_TASK, italic=True),
    "kmd.task_stack_prefix": Style(color=COLOR_HINT, italic=False),
    # Emoji colors:
    "kmd.task": Style(color=COLOR_TASK, italic=True),
    "kmd.success": Style(color=COLOR_SUCCESSS, bold=True),
    "kmd.skip": Style(color=COLOR_SKIP, bold=True),
    "kmd.failure": Style(color=COLOR_ERROR, bold=True),
    "kmd.timing": Style(color=COLOR_TIMING, bold=True),
    "kmd.warn": Style(color=COLOR_VALUE, bold=True),
    "kmd.saved": Style(color=COLOR_SAVED, bold=True),
    "kmd.log_call": Style(color=COLOR_CALL, bold=True),
    "kmd.box_chars": Style(color=COLOR_HINT),
}
