import html
from textwrap import indent
from typing import Any, Iterable
import regex


def format_lines(values: Iterable[Any], prefix="    ") -> str:
    """
    Simple indented or prefixed formatting of values one per line.
    """
    return indent("\n".join(str(value) for value in values), prefix)


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


def _trim_trailing_punctuation(text: str) -> str:
    return regex.sub(r"[.,;:!?]+$", "", text)


def abbreviate_on_words(text: str, max_len: int, indicator: str = "…") -> str:
    """
    Abbreviate text to a maximum length, breaking on whole words.
    """
    if len(text) <= max_len:
        return text
    words = text.split()
    while words and len(_trim_trailing_punctuation(" ".join(words))) + len(indicator) > max_len:
        words.pop()
    return _trim_trailing_punctuation(" ".join(words)) + indicator


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
    assert abbreviate_on_words("Hello, World!", 5) == "…"
    assert abbreviate_on_words("Hello, World!", 6) == "Hello…"
    assert abbreviate_on_words("Hello, World!", 13) == "Hello, World!"
    assert abbreviate_on_words("Hello, World!", 12) == "Hello…"
    assert abbreviate_on_words("", 2) == ""
    assert abbreviate_on_words("Hello, World!", 0) == "…"
    assert abbreviate_on_words("", 5) == ""