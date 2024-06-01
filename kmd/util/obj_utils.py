from dataclasses import asdict, is_dataclass
from enum import Enum
import operator
from strif import abbreviate_str
from typing import Any, Callable, Dict


def remove_value(data: Any, target: Any, eq: Callable[[Any, Any], bool] = operator.eq) -> Any:
    """
    Recursively remove all occurrences of the target value from a data structure.
    """
    if isinstance(data, dict):
        return {k: remove_value(v, target) for k, v in data.items() if not eq(v, target)}
    elif isinstance(data, list):
        return [remove_value(item, target) for item in data if not eq(item, target)]
    elif eq(data, target):
        return None
    else:
        return data


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
