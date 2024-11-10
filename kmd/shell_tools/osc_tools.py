import os

from cachetools import cached


@cached({})
def _terminal_supports_osc8() -> bool:
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


def osc8_link(url: str, text: str, metadata_str: str = "") -> str:
    r"""
    Return a string with the OSC 8 hyperlink escape sequence.

    Format: ESC ] 8 ; params ; URI ST text ESC ] 8 ; ; ST

    ST (String Terminator) is either ESC \ or BEL but the former is more common.

    Spec: https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda

    :param url: The URL for the hyperlink.
    :param text: The clickable text to display.
    :param metadata_str: Optional metadata between the semicolons.
    """
    st_code = "\x1b\\"
    safe_url = url.replace(";", "%3B")  # Escape semicolons in the URL.
    escape_start = f"\x1b]8;{metadata_str};{safe_url}{st_code}"
    escape_end = f"\x1b]8;;{st_code}"

    return f"{escape_start}{text}{escape_end}"


def osc8_link_graceful(url: str, text: str, id: str = "") -> str:
    """
    Generate clickable text for terminal emulators supporting OSC 8 with a fallback
    for non-supporting terminals.
    """
    if _terminal_supports_osc8():
        metadata_str = f"id={id}" if id else ""
        return osc8_link(url, text, metadata_str)
    else:
        # Fallback for non-supporting terminals.
        return f"{text} ({url})"
