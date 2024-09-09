"""
Settings that define the visual appearance of text outputs.
"""

from kmd.config import colors

## Settings

CONSOLE_WRAP_WIDTH = 80
"""Wrap width for console output."""

SPINNER = "dots12"
"""Progress spinner. For a list, use `python -m rich.spinner`."""

BAT_THEME = "Coldark-Dark"

## Text styles

LOGO = "⎪K⎪M⎪D⎪"


## Prompt coplors

PROMPT_COLOR_NORMAL = "BOLD_GREEN"

PROMPT_COLOR_WARN = "INTENSE_YELLOW"

INPUT_COLOR = colors.input


## Colors

COLOR_LOGO = "bold magenta"

COLOR_PLAIN = "default"

COLOR_HEADING = "bold bright_green"

COLOR_EMPH = "bright_green"

COLOR_EMPH_ALT = "bright_green"

COLOR_STATUS = "yellow"

COLOR_RESULT = "default"

COLOR_PROMPT = "yellow"

COLOR_HELP = "bright_blue"

COLOR_ASSISTANCE = "italic bright_blue"

COLOR_RESPONSE = "bright_blue"

COLOR_LITERAL = "bright_blue"

COLOR_KEY = "bright_blue"

COLOR_VALUE = "cyan"

COLOR_PATH = "cyan"

COLOR_HINT = "bright_black"

COLOR_SUCCESSS = "green"

COLOR_WARN = "bright_red"

COLOR_ERROR = "bright_red"

COLOR_TASK = "magenta"

COLOR_SAVED = "blue"

COLOR_TIMING = "blue"

COLOR_CALL = "yellow"

COLOR_COMMAND_TEXT = "bold default"

COLOR_ACTION_TEXT = "bold default"


## Formatting

NBSP = "\u00a0"

HRULE = ("⋯ " * (CONSOLE_WRAP_WIDTH // 2)).strip()

HRULE_SHORT = ("⋯ " * 20).strip()

## Symbols

SYMBOL_SEP = "⎪"

SYMBOL_PARA = "¶"

SYMBOL_SENT = "S"


## Symbols and emojis

PROMPT_MAIN = "❯"

PROMPT_ASSIST = "(help) ❯"

EMOJI_HINT = "👉"

EMOJI_TASK = "⛭"

EMOJI_WARN = "△"

EMOJI_SAVED = "⩣"

EMOJI_TIMING = "⏱"

EMOJI_SUCCESS = "✓"

EMOJI_CALL_BEGIN = "≫"

EMOJI_CALL_END = "≪"

EMOJI_ASSISTANT = "🤖"

EMOJI_TRUE = "✓"

EMOJI_FALSE = "✗"

EMOJI_TASK_SEP = "›"


## Rich setup

from rich.highlighter import RegexHighlighter, _combine_regex
from rich.style import Style


class KmdHighlighter(RegexHighlighter):
    """
    Highlighter based on the repr highighter with additions.
    """

    base_style = "kmd."
    highlights = [
        r"(?P<tag_start><)(?P<tag_name>[-\w.:|]*)(?P<tag_contents>[\w\W]*)(?P<tag_end>>)",
        r'(?P<attrib_name>[\w_-]{1,50})=(?P<attrib_value>"?[\w_]+"?)?',
        r"(?P<brace>[][{}()])",
        _combine_regex(
            r"(?P<ipv4>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            # Disabling ipv6 and EUI as these as they can have false positives.
            # r"(?P<ipv6>([A-Fa-f0-9]{1,4}::?){1,7}[A-Fa-f0-9]{1,4})",
            # r"(?P<eui64>(?:[0-9A-Fa-f]{1,2}-){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){3}[0-9A-Fa-f]{4})",
            # r"(?P<eui48>(?:[0-9A-Fa-f]{1,2}-){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})",
            r"(?P<uuid>[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
            r"(?P<call>[\w.]*?)\(",
            r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
            r"(?P<ellipsis>(\.\.\.|…))",
            r"(?P<part_count>\w+ \d+ of \d+(?!\-\w))",
            # r"(?P<number_complex>(?<!\w)(?:\-?[0-9]+\.?[0-9]*(?:e[-+]?\d+?)?)(?:[-+](?:[0-9]+\.?[0-9]*(?:e[-+]?\d+)?))?j)",
            # r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b(?!\-\w)|0x[0-9a-fA-F]*)",
            r"(?P<duration>(?<!\w)\-?[0-9]+\.?[0-9]*(ms|s)\b(?!\-\w))",
            r"(?P<path>\B(/[-\w._+]+)*\/)(?P<filename>[-\w._+]*)?",
            r"(?<![\\\w])(?P<str>b?'''.*?(?<!\\)'''|b?'.*?(?<!\\)'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
            r"(?P<url>(file|https|http|ws|wss)://[-0-9a-zA-Z$_+!`(),.?/;:&=%#~]*)",
            r"(?P<code_span>`[^`]+`)",
            # Task stack in logs:
            f"(?P<task_stack>{EMOJI_TASK}.*$)",
            f"(?P<task_stack_prefix>{EMOJI_TASK_SEP})",
            # Emoji colors:
            f"(?P<task>{EMOJI_TASK})",
            f"(?P<success>{EMOJI_SUCCESS})",
            f"(?P<timing>{EMOJI_TIMING})",
            f"(?P<warn>{EMOJI_WARN})",
            f"(?P<saved>{EMOJI_SAVED})",
            f"(?P<log_call>{EMOJI_CALL_BEGIN}|{EMOJI_CALL_END})",
            f"(?P<hrule>{HRULE})",
        ),
    ]

    # TODO: Recognize file sizes, "5 days ago" etc, relative paths.
    # r"(?P<time_ago>(?<!\w)[0-9]+ \w+ ago\b)"
    # r"(?P<file_size>(?<!\w)[0-9]+ ?([kKmMgGtTpP]B|Bytes|bytes)\b)",
    # r"(?P<relpath>\B([\w._+][-\w._+]*)*(/\w[-\w._+]*)+)*\.(html|htm|pdf|yaml|yml|md|txt)",


RICH_STYLES = {
    "markdown.h1": Style(color=COLOR_EMPH, bold=True),
    "markdown.h2": Style(color=COLOR_EMPH, bold=True),
    "markdown.h3": Style(color=COLOR_EMPH, bold=True, italic=True),
    "markdown.h4": Style(color=COLOR_EMPH_ALT, bold=True, italic=True),
    "kmd.ellipsis": Style(color=COLOR_HINT),
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
    "kmd.part_count": Style(color=COLOR_KEY, italic=False),
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
    "kmd.filename": Style(color=COLOR_VALUE),
    "kmd.task_stack": Style(color=COLOR_TASK, italic=True),
    "kmd.task_stack_prefix": Style(color=COLOR_HINT, italic=True),
    # Emoji colors:
    "kmd.task": Style(color=COLOR_TASK, bold=True),
    "kmd.success": Style(color=COLOR_SUCCESSS, bold=True),
    "kmd.timing": Style(color=COLOR_TIMING, bold=True),
    "kmd.warn": Style(color=COLOR_VALUE, bold=True),
    "kmd.saved": Style(color=COLOR_SAVED, bold=True),
    "kmd.log_call": Style(color=COLOR_CALL, bold=True),
    "kmd.hrule": Style(color=COLOR_HINT),
}
