from dataclasses import asdict, is_dataclass
from enum import Enum
import operator
from typing import Any, Callable, Dict, List, Tuple
from strif import abbreviate_str


class _DeleteMe:
    pass


DELETE_VALUE = _DeleteMe()
"""Sentinel value to indicate a list or dict value should be deleted."""


DataTransform = List[Tuple[Any, Any]]  # List of (old_value, new_value) pairs


def replace_values(
    data: Any, transform: DataTransform, eq: Callable[[Any, Any], bool] = operator.eq
) -> Any:
    """
    Recursively replace or remove values from a data structure according to the provided list of
    replacement pairs `(old, new)`. If the new value is `DELETE_VALUE`, the old value is removed
    from list and dictionary values.
    """
    for old_value, new_value in transform:
        if eq(data, old_value):
            if new_value is DELETE_VALUE:
                return None
            else:
                return new_value

    if isinstance(data, dict):
        return {
            k: replace_values(v, transform, eq)
            for k, v in data.items()
            if not any(
                eq(v, old_value) and new_value is DELETE_VALUE for old_value, new_value in transform
            )
        }
    elif isinstance(data, list):
        return [
            replace_values(item, transform, eq)
            for item in data
            if not any(
                eq(item, old_value) and new_value is DELETE_VALUE
                for old_value, new_value in transform
            )
        ]
    else:
        return data


def remove_values(
    data: Any, targets: List[Any], eq: Callable[[Any, Any], bool] = operator.eq
) -> Any:
    return replace_values(data, [(target, DELETE_VALUE) for target in targets], eq)


def abbreviate_value(value: Any, field_max_len: int) -> Dict[str, str]:
    if is_dataclass(value):
        value = asdict(value)
    if not isinstance(value, dict):
        raise ValueError(f"Value is not a dataclass instance or a dictionary: {type(value)}")

    return {
        k: repr(
            abbreviate_str(
                str(v.value) if isinstance(v, Enum) else str(v),
                max_len=field_max_len,
                indicator="[…]",
            )
        )
        for k, v in sorted(value.items())
        if v is not None
    }


def abbreviate_obj(value: Any, field_max_len: int = 64) -> str:
    """
    Helper for __str__() on dataclass values or other dictionaries.
    Abbreviate long fields for readability.
    """
    if not is_dataclass(value):
        raise ValueError("The provided value is not a dataclass instance.")

    name = value.__class__.__name__
    summary = ", ".join([f"{k}={v}" for k, v in abbreviate_value(value, field_max_len).items()])
    return f"{name}({summary})"


## Tests


def test_replace_values():
    data = {"a": 1, "b": 2, "c": [3, 4, 5], "d": {"e": 6, "f": 7}}

    transform = [
        (1, None),
        (2, DELETE_VALUE),
        (3, "three"),
        (4, DELETE_VALUE),
        (6, None),
        (7, DELETE_VALUE),
    ]

    expected = {"a": None, "c": ["three", 5], "d": {"e": None}}

    transformed = replace_values(data, transform)

    assert transformed == expected
