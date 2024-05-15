from textwrap import indent
from typing import Any, Iterable, Optional
from inflect import engine

_inflect = engine()


def plural(word: str, count: Optional[int] = None) -> str:
    return _inflect.plural(word, count)  # type: ignore


def format_lines(values: Iterable[Any], prefix="    ") -> str:
    return indent("\n".join(str(value) for value in values), prefix)
