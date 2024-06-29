from typing import Optional
from inflect import engine
from kmd.util.lazy_object import lazyobject


@lazyobject
def inflect():
    return engine()


def plural(word: str, count: Optional[int] = None) -> str:
    """
    Pluralize a word.
    """
    return inflect.plural(word, count)  # type: ignore
