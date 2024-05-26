from typing import Optional
from inflect import engine

_inflect = engine()


def plural(word: str, count: Optional[int] = None) -> str:
    """
    Pluralize a word.
    """
    return _inflect.plural(word, count)  # type: ignore
