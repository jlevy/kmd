## Text styles

COLOR_HEADING = "cyan"

COLOR_EMPH = "bright_blue"

COLOR_OUTPUT = "yellow"

COLOR_PLAIN = "default"

COLOR_LITERAL = "yellow"

COLOR_KEY = "cyan"

COLOR_VALUE = "bright_blue"

COLOR_HINT = "bright_black"

COLOR_SUCCESSS = "bright_green"

COLOR_ERROR = "bright_red"

## Formatting

NBSP = "\u00A0"


## Symbols

SYMBOL_SEP = "⎪"

SYMBOL_PARA = "¶"

SYMBOL_SENT = "S"


## Emojis

EMOJI_PROCESS = "⛭"

EMOJI_WARN = "⚠️"

EMOJI_SAVED = "⩣"

EMOJI_TIME = "⏱️"

EMOJI_SUCCESS = "✔️"


## Rich setup

from rich.style import Style

RICH_STYLES = {
    "kmd.ellipsis": Style(color=COLOR_HINT),
    "kmd.indent": Style(color=COLOR_KEY, dim=True),
    "kmd.error": Style(color=COLOR_ERROR, bold=True),
    "kmd.str": Style(color=COLOR_LITERAL, italic=False, bold=False),
    "kmd.brace": Style(bold=True),
    "kmd.comma": Style(bold=True),
    "kmd.ipv4": Style(bold=True, color=COLOR_KEY),
    "kmd.ipv6": Style(bold=True, color=COLOR_KEY),
    "kmd.eui48": Style(bold=True, color=COLOR_KEY),
    "kmd.eui64": Style(bold=True, color=COLOR_KEY),
    "kmd.tag_start": Style(bold=True),
    "kmd.tag_name": Style(color=COLOR_VALUE, bold=True),
    "kmd.tag_contents": Style(color="default"),
    "kmd.tag_end": Style(bold=True),
    "kmd.attrib_name": Style(color=COLOR_KEY, italic=False),
    "kmd.attrib_equal": Style(bold=True),
    "kmd.attrib_value": Style(color=COLOR_VALUE, italic=False),
    "kmd.number": Style(color=COLOR_KEY, italic=False),
    "kmd.duration": Style(color=COLOR_KEY, italic=False),
    "kmd.number_complex": Style(color=COLOR_KEY, italic=False),  # same
    "kmd.bool_true": Style(color=COLOR_SUCCESSS, italic=True),
    "kmd.bool_false": Style(color=COLOR_ERROR, italic=True),
    "kmd.none": Style(color=COLOR_VALUE, italic=True),
    "kmd.url": Style(underline=True, color=COLOR_VALUE, italic=False, bold=False),
    "kmd.uuid": Style(color=COLOR_LITERAL, bold=False),
    "kmd.call": Style(color=COLOR_VALUE),
    "kmd.path": Style(color=COLOR_VALUE),
    "kmd.filename": Style(color=COLOR_VALUE),
}
