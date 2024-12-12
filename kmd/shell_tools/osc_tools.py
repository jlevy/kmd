import os
from functools import cache

from rich.style import Style
from rich.text import Text


@cache
def terminal_supports_osc8() -> bool:
    """
    Attempt to detect if the terminal supports OSC 8 hyperlinks.
    """
    term_program = os.environ.get("TERM_PROGRAM", "")
    term = os.environ.get("TERM", "")

    if term_program in ["iTerm.app", "WezTerm", "Hyper"]:
        return True
    if "konsole" in term_program.lower():
        return True
    if "kitty" in term or "xterm" in term:
        return True
    if "vscode" in term_program.lower():
        return True

    return False


# Constants for OSC control sequences
OSC_START = "\x1b]"
ST_CODE = "\x1b\\"  # String Terminator
BEL_CODE = "\x07"  # Bell character

OSC_HYPERLINK = "8"


def osc_code(code: str, data: str) -> str:
    """
    Return an extended OSC code.
    """
    return f"{OSC_START}{code};{data}{ST_CODE}"


def osc8_link(uri: str, text: str, metadata_str: str = "") -> str:
    r"""
    Return a string with the OSC 8 hyperlink escape sequence.

    Format: ESC ] 8 ; params ; URI ST text ESC ] 8 ; ; ST

    ST (String Terminator) is either ESC \ or BEL but the former is more common.

    Spec: https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda

    :param uri: The URI or URL for the hyperlink.
    :param text: The clickable text to display.
    :param metadata_str: Optional metadata between the semicolons.
    """
    safe_uri = uri.replace(";", "%3B")  # Escape semicolons in the URL.
    escape_start = f"{OSC_START}{OSC_HYPERLINK};{metadata_str};{safe_uri}{ST_CODE}"
    escape_end = f"{OSC_START}{OSC_HYPERLINK};;{ST_CODE}"

    return f"{escape_start}{text}{escape_end}"


def osc8_link_graceful(uri: str, text: str, id: str = "") -> str:
    """
    Generate clickable text for terminal emulators supporting OSC 8 with a fallback
    for non-supporting terminals to make the link visible.
    """
    if terminal_supports_osc8():
        metadata_str = f"id={id}" if id else ""
        return osc8_link(uri, text, metadata_str)
    else:
        # Fallback for non-supporting terminals.
        return f"{text} ({uri})"


def osc8_link_rich(uri: str, text: str, metadata_str: str = "", style: str | Style = "") -> Text:
    """
    Must use Text.from_ansi() for Rich to handle links correctly!
    """
    return Text.from_ansi(osc8_link(uri, text, metadata_str), style=style)
