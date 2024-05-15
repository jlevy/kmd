from typing import Optional, TypeVar

T = TypeVar("T")


def assert_not_none(value: Optional[T], message: Optional[str] = None) -> T:
    assert value is not None, message
    return value
