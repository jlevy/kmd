import html
from textwrap import indent
from typing import Any, Iterable
import regex
from strif import abbreviate_str


def format_lines(values: Iterable[Any], prefix: str = "    ", line_break: str = "\n") -> str:
    """
    Simple indented or prefixed formatting of values one per line.
    """
    return indent(line_break.join(str(value) for value in values), prefix).rstrip()


def plaintext_to_html(text: str):
    """
    Convert plaintext to HTML, also handling newlines and whitespace.
    """
    return (
        html.escape(text)
        .replace("\n", "<br>")
        .replace("\t", "&nbsp;" * 4)
        .replace("  ", "&nbsp;&nbsp;")
    )


def single_line(text: str) -> str:
    """
    Convert newlines and other whitespace to spaces.
    """
    return regex.sub(r"\s+", " ", text).strip()


def html_to_plaintext(text: str):
    """
    Convert HTML to plaintext, stripping tags and converting entities.
    """
    text = regex.sub(r"<br>", "\n", text, flags=regex.IGNORECASE)
    text = regex.sub(r"<p>", "\n\n", text, flags=regex.IGNORECASE)
    unescaped_text = html.unescape(text)
    clean_text = regex.sub("<[^<]+?>", "", unescaped_text)
    return clean_text


def clean_title(text: str) -> str:
    """
    Clean up arbitrary text to make it suitable for a title. Convert all whitespace to spaces.
    Only allows the most common punctuation, letters, and numbers, but not Markdown, code characters etc.
    """
    return regex.sub(r"[^\p{L}\p{N},./:;'!?/@%&()+“”‘’…–—-]+", " ", text).strip()


def clean_description(text: str) -> str:
    """
    Clean up txt to make it suitable for a description. Convert all whitespace to spaces.
    """
    return regex.sub(r"\s+", " ", text).strip()


def _trim_trailing_punctuation(text: str) -> str:
    return regex.sub(r"[.,;:!?]+$", "", text)


def abbreviate_on_words(text: str, max_len: int, indicator: str = "…") -> str:
    """
    Abbreviate text to a maximum length, breaking on whole words (unless the first word
    is too long). For aesthetics, removes trailing punctuation from the last word.
    """
    if len(text) <= max_len:
        return text
    words = text.split()

    if words and max_len and len(words[0]) > max_len:
        return abbreviate_str(words[0], max_len, indicator)

    while words and len(_trim_trailing_punctuation(" ".join(words))) + len(indicator) > max_len:
        words.pop()

    return _trim_trailing_punctuation(" ".join(words)) + indicator


def abbreviate_phrase_in_middle(
    phrase: str, max_len: int, ellipsis="…", max_trailing_len: int = 0
) -> str:
    """
    Abbreviate a phrase to a maximum length, preserving the first and last few words of
    the phrase whenever possible. The ellipsis is inserted in the middle of the phrase.
    """
    if not max_trailing_len:
        max_trailing_len = min(int(max_len / 2), max(16, int(max_len / 4)))

    phrase = " ".join(phrase.split())

    if len(phrase) <= max_len:
        return phrase

    if max_len <= len(ellipsis):
        return ellipsis

    words = phrase.split()
    prefix_tally = 0
    prefix_end_index = 0

    # Walk through the split words, and tally total number of chars as we go.
    for i in range(len(words)):
        words[i] = abbreviate_str(words[i], max_len, ellipsis)
        if prefix_tally + len(words[i]) + len(ellipsis) + max_trailing_len >= max_len and i > 0:
            prefix_end_index = i
            break
        prefix_tally += len(words[i]) + 1

    prefix_end_index = max(1, prefix_end_index)

    # Calculate the start index for the trailing part.
    suffix_start_index = len(words) - 1
    suffix_tally = 0
    for i in range(len(words) - 1, prefix_end_index - 1, -1):
        if suffix_tally + len(words[i]) + len(ellipsis) + prefix_tally > max_len:
            suffix_start_index = i + 1
            break
        suffix_tally += len(words[i]) + 1

    # Replace the middle part with ellipsis.
    words = words[:prefix_end_index] + [ellipsis] + words[suffix_start_index:]

    result = " ".join(word for word in words if word)

    return result


## Tests


def test_plaintext_to_html():
    assert plaintext_to_html("") == ""
    assert plaintext_to_html("Hello, World!") == "Hello, World!"
    assert plaintext_to_html("Hello\n  World!") == "Hello<br>&nbsp;&nbsp;World!"
    assert plaintext_to_html("Hello\tWorld!") == "Hello&nbsp;&nbsp;&nbsp;&nbsp;World!"
    assert plaintext_to_html("<Hello, World!>") == "&lt;Hello, World!&gt;"


def test_html_to_plaintext():
    assert html_to_plaintext("") == ""
    assert html_to_plaintext("<p>Hello, World!</p>") == "\n\nHello, World!"
    assert html_to_plaintext("<br>Hello, World!<br>") == "\nHello, World!\n"
    assert html_to_plaintext("<BR>Hello, World!<BR>") == "\nHello, World!\n"
    assert (
        html_to_plaintext(
            '<p>Hello,<br>World!<br><div>Hello, <span data-id="123">World!</span></div></p>'
        )
        == "\n\nHello,\nWorld!\nHello, World!"
    )


def test_clean_title():
    assert clean_title("Hello, World!") == "Hello, World!"
    assert clean_title("Hej, Världen!") == "Hej, Världen!"
    assert clean_title("你好 世界") == "你好 世界"
    assert clean_title("こんにちは、世界") == "こんにちは 世界"
    assert clean_title(" *Hello,*  \n\tWorld!  --123@:': ") == "Hello, World! --123@:':"
    assert clean_title("<script foo='blah'><p>") == "script foo 'blah' p"


def test_abbreviate_on_words():
    assert abbreviate_on_words("Hello, World!", 5) == "Hell…"
    assert abbreviate_on_words("Hello, World!", 6) == "Hello…"
    assert abbreviate_on_words("Hello, World!", 13) == "Hello, World!"
    assert abbreviate_on_words("Hello, World!", 12) == "Hello…"
    assert abbreviate_on_words("", 2) == ""
    assert abbreviate_on_words("Hello, World!", 0) == "…"
    assert abbreviate_on_words("", 5) == ""
    assert (
        abbreviate_on_words("Supercalifragilisticexpialidocious is a long word", 20)
        == "Supercalifragilisti…"
    )


def test_abbreviate_phrase_in_middle():
    assert abbreviate_phrase_in_middle("Hello, World! This is a test.", 16) == "Hello, … a test."
    assert (
        abbreviate_phrase_in_middle("Hello, World! This is a test.", 23)
        == "Hello, … This is a test."
    )
    assert (
        abbreviate_phrase_in_middle("Hello, World! This is a test.", 27)
        == "Hello, … This is a test."
    )
    assert (
        abbreviate_phrase_in_middle("Hello, World! This is a test.", 40)
        == "Hello, World! This is a test."
    )
    assert abbreviate_phrase_in_middle("Hello, World! This is a test.", 10) == "Hello, …"
    assert (
        abbreviate_phrase_in_middle("Supercalifragilisticexpialidocious is a long word", 24)
        == "Supercalifragilisticexp… …"
    )

    assert (
        abbreviate_phrase_in_middle(
            "Your Mindset Matters (transcription) (clean text) (in paragraphs) (with timestamps) (add_description)",
            64,
        )
        == "Your Mindset Matters (transcription) (clean … (add_description)"
    )
