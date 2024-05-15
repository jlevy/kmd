from textwrap import indent
from typing import Any, Iterable, Optional
from inflect import engine
import regex

_inflect = engine()


def plural(word: str, count: Optional[int] = None) -> str:
    return _inflect.plural(word, count)  # type: ignore


def format_lines(values: Iterable[Any], prefix="    ") -> str:
    return indent("\n".join(str(value) for value in values), prefix)


def clean_title(text: str) -> str:
    """
    Clean up arbitrary text to make it suitable for a title.
    Only allows the most common punctuation, letters, and numbers, but not Markdown, code characters etc.
    """
    return regex.sub(r"[^\p{L}\p{N},./:;'!?/@%&()+“”‘’…–—-]+", " ", text).strip()


def test_clean_title():
    assert clean_title("Hello, World!") == "Hello, World!"
    assert clean_title("Hej, Världen!") == "Hej, Världen!"
    assert clean_title("你好 世界") == "你好 世界"
    assert clean_title("こんにちは、世界") == "こんにちは 世界"
    assert clean_title(" *Hello,*  \n\tWorld!  --123@:': ") == "Hello, World! --123@:':"
    assert clean_title("<script foo='blah'><p>") == "script foo 'blah' p"
