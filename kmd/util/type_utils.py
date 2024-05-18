from typing import Optional, TypeVar

T = TypeVar("T")


def not_none(value: Optional[T], message: Optional[str] = None) -> T:
    """
    Fluent assertion that the given value is not None.
    """
    assert value is not None, message
    return value
