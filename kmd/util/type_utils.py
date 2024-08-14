from typing import Any, Dict, Optional, Type, TypeVar, get_args, get_origin
from dataclasses import is_dataclass, fields

T = TypeVar("T")


def not_none(value: Optional[T], message: Optional[str] = None) -> T:
    """
    Fluent assertion that the given value is not None.
    """
    if value is None:
        raise ValueError(message or "Unexpected None value")
    return value


def is_truthy(value: Any, strict: bool = True) -> bool:
    """
    True for all common string and non-string values for true.
    """
    truthy_values = {"true", "1", "yes", "on", "y"}
    falsy_values = {"false", "0", "no", "off", "n", ""}

    if value is None:
        return False
    elif isinstance(value, str):
        value = value.strip().lower()
        if value in truthy_values:
            return True
        elif value in falsy_values:
            return False
    elif isinstance(value, (int, float)):
        return value != 0
    elif isinstance(value, bool):
        return value
    elif isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0

    if strict:
        raise ValueError(f"Could not convert type {type(value)} to boolean: {repr(value)}")

    return bool(value)


def as_dataclass(dict_data: Dict[str, Any], dataclass_type: Type[T]) -> T:
    """
    Convert a dict recursively to dataclass object, raising an error if the data does
    not fit the dataclass. Can be used to validate a deserialized dict is compatible
    with the dataclass's constructor.
    """

    field_types = {f.name: f.type for f in fields(dataclass_type)}
    dataclass_fields = {}

    for k, v in dict_data.items():
        field_type = field_types[k]
        origin_type = get_origin(field_type)

        if origin_type is list and isinstance(v, list):
            item_type = get_args(field_type)[0]
            if is_dataclass(item_type):
                dataclass_fields[k] = [as_dataclass(item, item_type) for item in v]
            else:
                dataclass_fields[k] = v
        elif is_dataclass(field_type) and isinstance(v, dict):
            dataclass_fields[k] = as_dataclass(v, field_type)
        else:
            dataclass_fields[k] = v

    return dataclass_type(**dataclass_fields)
