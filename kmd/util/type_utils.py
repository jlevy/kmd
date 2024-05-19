from typing import Any, Dict, Optional, Type, TypeVar, get_args, get_origin
from dataclasses import is_dataclass, fields

T = TypeVar("T")


def not_none(value: Optional[T], message: Optional[str] = None) -> T:
    """
    Fluent assertion that the given value is not None.
    """
    assert value is not None, message
    return value


def as_dataclass(dict_data: Dict[str, Any], dataclass_type: Type[T]) -> T:
    """
    Convert a dict recursively to dataclass object, raising an error if the data does not fit the dataclass.
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
