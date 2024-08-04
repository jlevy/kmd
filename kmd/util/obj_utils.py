from dataclasses import asdict, is_dataclass
from enum import Enum
import operator
from typing import Any, Callable, Iterable, List, Optional, Set, Tuple
from strif import abbreviate_str
from kmd.util.log_calls import quote_if_needed


class DeleteSentinel:
    pass


DELETE_VALUE = DeleteSentinel()
"""Sentinel value to indicate a list or dict value should be deleted."""


ValueReplacements = List[Tuple[Any, Any]]  # List of (old_value, new_value) pairs


def replace_values(
    data: Any, transform: ValueReplacements, eq: Callable[[Any, Any], bool] = operator.eq
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


def is_not_none(value: Any) -> bool:
    return value is not None


def _format_kvs(
    items: Iterable[Tuple[Any, Any]],
    field_max_len: int,
    value_filter: Callable[[Any], bool] = is_not_none,
) -> str:
    abbreviated_items = {k: abbreviate_obj(v, field_max_len) for k, v in items if value_filter(v)}
    return ", ".join(f"{k}={v}" for k, v in abbreviated_items.items())


def abbreviate_obj(
    value: Any,
    field_max_len: int = 64,
    list_max_len: int = 32,
    value_filter: Callable[[Any], bool] = is_not_none,
    visited: Optional[Set[Any]] = None,
) -> str:
    """
    Helper to print an abbreviated string version of an object. Not a parsable format.
    Useful for abbreviating dicts or for __str__() on dataclasses. Abbreviate long
    fields for readability, omit None values, and omit quotes when possible.
    """
    if visited is None:
        visited = set()
    if id(value) in visited:
        return "<circular reference>"
    visited.add(id(value))

    if isinstance(value, list):
        truncated_list = value[:list_max_len] + (["..."] if len(value) > list_max_len else [])
        return (
            "["
            + ", ".join(
                abbreviate_obj(item, field_max_len, list_max_len, value_filter, visited)
                for item in truncated_list
            )
            + "]"
        )

    if is_dataclass(value):
        name = value.__class__.__name__
        value_dict = asdict(value)
        return f"{name}(" + _format_kvs(value_dict.items(), field_max_len, value_filter) + ")"

    if isinstance(value, dict):
        return "{" + _format_kvs(value.items(), field_max_len, value_filter) + "}"

    if isinstance(value, Enum):
        return value.name

    return quote_if_needed(abbreviate_str(str(value), field_max_len))


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
