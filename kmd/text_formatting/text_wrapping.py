import re
from textwrap import dedent
from typing import List, Protocol, Tuple

from kmd.util.ansi_cell_len import ansi_cell_len

# wrap_length_fn = len
wrap_length_fn = ansi_cell_len
"""
Length function to use for wrapping.
We could use character length, but ansi_cell_len is more accurate for OSC 8 links.
"""


class WordSplitter(Protocol):
    def __call__(self, text: str) -> List[str]: ...


def simple_word_splitter(text: str) -> List[str]:
    """
    Split words on whitespace.
    """
    return text.split()


class _HtmlMdWordSplitter:
    def __init__(self):
        # Sequences of whitespace-delimited words that should be coalesced and treated
        # like a single word.
        self.patterns = [
            # HTML tags:
            (r"<[^>]+", r"[^<>]+>[^<>]*"),
            (r"<[^>]+", r"[^<>]+", r"[^<>]+>[^<>]*"),
            # Markdown links:
            (r"\[", r"[^\[\]]+\][^\[\]]*"),
            (r"\[", r"[^\[\]]+", r"[^\[\]]+\][^\[\]]*"),
        ]
        self.compiled_patterns = [
            tuple(re.compile(pattern) for pattern in pattern_group)
            for pattern_group in self.patterns
        ]

    def __call__(self, text: str) -> List[str]:
        words = text.split()
        result = []
        i = 0
        while i < len(words):
            coalesced = self.coalesce_words(words[i:])
            if coalesced > 0:
                result.append(" ".join(words[i : i + coalesced]))
                i += coalesced
            else:
                result.append(words[i])
                i += 1
        return result

    def coalesce_words(self, words: List[str]) -> int:
        for pattern_group in self.compiled_patterns:
            if self.match_pattern_group(words, pattern_group):
                return len(pattern_group)
        return 0

    def match_pattern_group(self, words: List[str], patterns: Tuple[re.Pattern, ...]) -> bool:
        if len(words) < len(patterns):
            return False

        return all(pattern.match(word) for pattern, word in zip(patterns, words))


html_md_word_splitter = _HtmlMdWordSplitter()
"""
Split words, but not within HTML tags or Markdown links.
"""


def wrap_text(
    text: str,
    width: int,
    initial_offset: int = 0,
    subsequent_offset: int = 0,
    replace_whitespace: bool = True,
    drop_whitespace: bool = True,
    splitter: WordSplitter = html_md_word_splitter,
) -> List[str]:
    """
    Wrap a single paragraph of text, returning a list of wrapped lines.
    Rewritten to simplify and generalize Python's textwrap.py.
    """
    len_fn = wrap_length_fn

    if replace_whitespace:
        text = re.sub(r"\s+", " ", text)

    words = splitter(text)

    lines: List[str] = []
    current_line: List[str] = []
    current_width = initial_offset

    # Special case: if the first word would not fit due to the initial_offset,
    # add a blank line to indicate we must begin a new line.
    # if initial_offset > 0 and len(words) > 0 and initial_offset + len(words[0]) > width:
    #     lines.append("")
    #     current_width = subsequent_offset
    #     initial_offset = subsequent_offset

    # Walk through words, breaking them into lines.
    for word in words:
        word_width = len_fn(word)

        space_width = 1 if current_line else 0
        if current_width + word_width + space_width <= width:
            # Add word to current line.
            current_line.append(word)
            current_width += word_width + space_width
        else:
            # Start a new line.
            if current_line:
                line = " ".join(current_line)
                if drop_whitespace:
                    line = line.strip()
                lines.append(line)
            current_line = [word]
            current_width = subsequent_offset + word_width

    if current_line:
        line = " ".join(current_line)
        if drop_whitespace:
            line = line.strip()
        lines.append(line)

    return lines


def wrap_paragraph(
    text: str,
    width: int,
    initial_indent: str = "",
    subsequent_indent: str = "",
    initial_offset: int = 0,
    replace_whitespace: bool = True,
    drop_whitespace: bool = True,
    splitter: WordSplitter = html_md_word_splitter,
) -> str:
    """
    Fill a single paragraph of text, returning a new string.
    """
    lines = wrap_text(
        text=text,
        width=width,
        replace_whitespace=replace_whitespace,
        drop_whitespace=drop_whitespace,
        splitter=splitter,
        initial_offset=initial_offset + wrap_length_fn(initial_indent),
        subsequent_offset=wrap_length_fn(subsequent_indent),
    )
    # Now insert indents on first and subsequent lines, if needed.
    if initial_indent and initial_offset == 0 and len(lines) > 0:
        lines[0] = initial_indent + lines[0]
    if subsequent_indent and len(lines) > 1:
        lines[1:] = [subsequent_indent + line for line in lines[1:]]
    return "\n".join(lines)


# Tests


def test_smart_splitter():
    splitter = _HtmlMdWordSplitter()

    html_text = "This is <span class='test'>some text</span> and <a href='#'>this is a link</a>."
    assert splitter(html_text) == [
        "This",
        "is",
        "<span class='test'>some",
        "text</span>",
        "and",
        "<a href='#'>this",
        "is",
        "a",
        "link</a>.",
    ]

    md_text = "Here's a [Markdown link](https://example.com) and [another one](https://test.com)."
    assert splitter(md_text) == [
        "Here's",
        "a",
        "[Markdown link](https://example.com)",
        "and",
        "[another one](https://test.com).",
    ]

    mixed_text = "Text with <b>bold</b> and [a link](https://example.com)."
    assert splitter(mixed_text) == [
        "Text",
        "with",
        "<b>bold</b>",
        "and",
        "[a link](https://example.com).",
    ]


def test_wrap_text():
    sample_text = (
        "This is a sample text with a [Markdown link](https://example.com)"
        " and an <a href='#'>tag</a>. It should demonstrate the functionality of "
        "our enhanced text wrapping implementation."
    )

    print("\nFilled text with default splitter:")
    filled = wrap_paragraph(
        sample_text,
        splitter=simple_word_splitter,
        width=40,
        initial_indent=">",
        subsequent_indent=">>",
    )
    print(filled)
    filled_expected = dedent(
        """
        >This is a sample text with a [Markdown
        >>link](https://example.com) and an <a
        >>href='#'>tag</a>. It should
        >>demonstrate the functionality of our
        >>enhanced text wrapping implementation.
        """
    ).strip()

    print("\nFilled text with html_md_word_splitter:")
    filled_smart = wrap_paragraph(
        sample_text,
        splitter=html_md_word_splitter,
        width=40,
        initial_indent=">",
        subsequent_indent=">>",
    )
    print(filled_smart)
    filled_smart_expected = dedent(
        """
        >This is a sample text with a
        >>[Markdown link](https://example.com)
        >>and an <a href='#'>tag</a>. It should
        >>demonstrate the functionality of our
        >>enhanced text wrapping implementation.
        """
    ).strip()

    print("\nFilled text with html_md_word_splitter and initial_offset:")
    filled_smart_offset = wrap_paragraph(
        sample_text,
        splitter=html_md_word_splitter,
        width=40,
        initial_indent=">",
        subsequent_indent=">>",
        initial_offset=35,
    )
    print(filled_smart_offset)
    filled_smart_offset_expected = dedent(
        """
        This
        >>is a sample text with a
        >>[Markdown link](https://example.com)
        >>and an <a href='#'>tag</a>. It should
        >>demonstrate the functionality of our
        >>enhanced text wrapping implementation.
        """
    ).strip()

    assert filled == filled_expected
    assert filled_smart == filled_smart_expected
    assert filled_smart_offset == filled_smart_offset_expected


def test_wrap_width():
    text = dedent(
        """
        You may also simply ask a question and the Kmd assistant will help you. Press
        `?` or just press space twice, then write your question or request. Press `?` and
        tab to get suggested questions.
        """
    ).strip()
    width = 80
    wrapped = wrap_text(text, width=width)
    print(wrapped)
    print([len(line) for line in wrapped])
    assert all(len(line) <= width for line in wrapped)


def test_osc8_link():
    from kmd.shell_tools.osc_tools import osc8_link

    link = osc8_link("https://example.com/" + "x" * 50, "Example")
    assert ansi_cell_len(link) == 7
    text = (link + " ") * 50
    wrapped = wrap_paragraph(text, width=80).splitlines()
    print([ansi_cell_len(line) for line in wrapped])
    print([len(line) for line in wrapped])
    assert all(ansi_cell_len(line) <= 80 for line in wrapped)
    assert all(len(line) >= 800 for line in wrapped)
