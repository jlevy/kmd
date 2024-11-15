"""
Monkey-patch to fix Rich's cell_len method to correctly handle OSC-8 links.
"""

from functools import lru_cache
from typing import Callable

import rich.cells
from rich.cells import _is_single_cell_widths, get_character_cell_size


def strip_control_sequences(text: str) -> str:
    """Strips ANSI control sequences, including OSC-8 links, from the text."""
    from rich.ansi import _ansi_tokenize

    plain_text_parts = []
    for token in _ansi_tokenize(text):
        if token.plain:
            plain_text_parts.append(token.plain)
    return "".join(plain_text_parts)


@lru_cache(4096)  # noqa: F821
def cached_cell_len(text: str) -> int:
    """Get the number of cells required to display text.

    This method always caches, which may use up a lot of memory. It is recommended to use
    `cell_len` over this method.

    Args:
        text (str): Text to display.

    Returns:
        int: Get the number of cells required to display text.
    """
    if _is_single_cell_widths(text):
        return len(text)
    return sum(map(get_character_cell_size, strip_control_sequences(text)))


def cell_len(text: str, _cell_len: Callable[[str], int] = cached_cell_len) -> int:
    """Get the number of cells required to display text.

    Args:
        text (str): Text to display.

    Returns:
        int: Get the number of cells required to display text.
    """
    if len(text) < 512:
        return _cell_len(text)
    if _is_single_cell_widths(text):
        return len(text)
    return sum(map(get_character_cell_size, strip_control_sequences(text)))


# Monkey patch!
rich.cells.cached_cell_len = cached_cell_len
rich.cells.cell_len = cell_len


## Tests


def _make_osc_link(url: str, text: str) -> str:
    return f"\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\"


_plain_text = "ansi🤔"
_short_osc_link = _make_osc_link("http://example.com/", _plain_text)
_long_osc_link = _make_osc_link("http://example.com/" + "x" * 100, _plain_text)


def test_old_cell_len_bug():
    from rich.cells import cell_len as old_cell_len

    print(
        f"old lengths: plain_text={old_cell_len(_plain_text)} "
        f"short_osc_link={old_cell_len(_short_osc_link)} "
        f"long_osc_link={old_cell_len(_long_osc_link)}"
    )
    assert old_cell_len(_plain_text) == 6
    # Without patching:
    # assert old_cell_len(_short_osc_link) == 35  # Wrong!
    # assert old_cell_len(_long_osc_link) == 135  # Wrong!
    # If this patch is loaded:
    assert old_cell_len(_short_osc_link) == cell_len(_short_osc_link)
    assert old_cell_len(_long_osc_link) == cell_len(_long_osc_link)


def test_cell_len():

    print(
        f"new lengths: plain_text={cell_len(_plain_text)} "
        f"short_osc_link={cell_len(_short_osc_link)} "
        f"long_osc_link={cell_len(_long_osc_link)}"
    )
    assert cell_len(_plain_text) == 6
    assert cell_len(_short_osc_link) == cell_len(_plain_text)
    assert cell_len(_long_osc_link) == cell_len(_plain_text)
