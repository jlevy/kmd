import re
from typing import List


def wrap_text(
    text: str,
    width: int = 70,
    initial_indent: str = "",
    subsequent_indent: str = "",
    replace_whitespace: bool = True,
    drop_whitespace: bool = True,
) -> List[str]:
    """
    Wrap a single paragraph of text, returning a list of wrapped lines.
    Rewritten and simplified from Python's textwrap.py.

    :param initial_indent: String to prepend to the first line.
    :param subsequent_indent: String to prepend to subsequent lines.
    :param replace_whitespace: Replace all whitespace with single spaces.
    :param drop_whitespace: Drop leading and trailing whitespace from lines.
    """
    if replace_whitespace:
        text = re.sub(r"\s+", " ", text)

    words = text.split()

    lines: List[str] = []
    current_line: List[str] = []
    current_width = len(initial_indent)

    for word in words:
        word_width = len(word)

        if current_width + word_width <= width:
            current_line.append(word)
            current_width += word_width + 1  # +1 for space.
        else:
            if current_line:
                line = " ".join(current_line)
                if drop_whitespace:
                    line = line.strip()
                lines.append((initial_indent if not lines else subsequent_indent) + line)
            current_line = [word]
            current_width = len(subsequent_indent) + word_width

    if current_line:
        line = " ".join(current_line)
        if drop_whitespace:
            line = line.strip()
        lines.append((initial_indent if not lines else subsequent_indent) + line)

    return lines


def text_wrap_fill(text: str, width: int = 70, **kwargs) -> str:
    """
    Fill a single paragraph of text, returning a new string.
    """
    return "\n".join(wrap_text(text, width, **kwargs))


## Tests


def test_fill_text():
    sample_text = "This is a sample text that we want to wrap. It should demonstrate the functionality of our simplified text wrapping implementation."
    expected_filled = (
        "> This is a sample text that we want to\n"
        ">>  wrap. It should demonstrate the\n"
        ">>  functionality of our simplified text\n"
        ">>  wrapping implementation."
    )
    filled = text_wrap_fill(sample_text, width=40, initial_indent="> ", subsequent_indent=">>  ")
    assert filled == expected_filled
