import re
from textwrap import dedent
from typing import List, Protocol, Tuple


class WordSplitter(Protocol):
    def __call__(self, text: str) -> List[str]: ...


def simple_word_splitter(text: str) -> List[str]:
    """
    Split words on whitespace.
    """
    return text.split()


class _SmarterWordSplitter:
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


smarter_word_splitter = _SmarterWordSplitter()
"""
Split words, but not within HTML tags or Markdown links.
"""


def wrap_text(
    text: str,
    width: int,
    initial_indent: str = "",
    subsequent_indent: str = "",
    empty_indent: str = "",
    replace_whitespace: bool = True,
    drop_whitespace: bool = True,
    splitter: WordSplitter = smarter_word_splitter,
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

    words = splitter(text)

    lines: List[str] = []
    current_line: List[str] = []
    current_width = len(initial_indent)

    for word in words:
        word_width = len(word)

        space_width = 1 if current_line else 0
        if current_width + word_width + space_width <= width:
            current_line.append(word)
            current_width += word_width + space_width
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
    elif empty_indent:
        lines.append(empty_indent)

    return lines


def wrap_paragraph(
    text: str,
    width: int,
    initial_indent: str = "",
    subsequent_indent: str = "",
    empty_indent: str = "",
    replace_whitespace: bool = True,
    drop_whitespace: bool = True,
    splitter: WordSplitter = smarter_word_splitter,
) -> str:
    """
    Fill a single paragraph of text, returning a new string.
    """
    return "\n".join(
        wrap_text(
            text,
            width,
            initial_indent,
            subsequent_indent,
            empty_indent,
            replace_whitespace,
            drop_whitespace,
            splitter,
        )
    )


# Tests


def test_smart_splitter():
    splitter = _SmarterWordSplitter()

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

    print("\nFilled text with smart splitter:")
    filled_smart = wrap_paragraph(
        sample_text,
        splitter=smarter_word_splitter,
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

    assert filled == filled_expected

    assert filled_smart == filled_smart_expected


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
