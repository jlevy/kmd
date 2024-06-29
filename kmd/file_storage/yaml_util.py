"""
YAML file storage.
"""

from io import StringIO
import os
from typing import Any, Callable, List, Optional, TextIO
from ruamel.yaml import YAML
from strif import atomic_output_file

KeySort = Callable[[str], tuple]


def _new_yaml(key_sort: Optional[KeySort] = None) -> YAML:
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False  # Block style dictionaries.

    # Ignore None values in output. Sort keys if key_sort is provided.
    def represent_dict(dumper, data):
        if key_sort:
            data = {k: data[k] for k in sorted(data.keys(), key=key_sort)}
        return dumper.represent_dict({k: v for k, v in data.items() if v is not None})

    yaml.representer.add_representer(dict, represent_dict)
    if key_sort:
        yaml.representer.sort_base_mapping_type_on_output = False

    return yaml


def custom_key_sort(priority_keys: List[str]) -> KeySort:
    """
    Custom sort function that prioritizes the specific keys in a certain order, followed
    by all the other keys in natural order.
    """

    def sort_func(key):
        try:
            i = priority_keys.index(key)
            return (i, key)
        except ValueError:
            return (float("inf"), key)

    return sort_func


def from_yaml_string(yaml_string: str) -> Any:
    """
    Read a YAML string into a Python object.
    """
    return _new_yaml().load(yaml_string)


def read_yaml_file(filename: str) -> Any:
    """
    Read YAML file into a Python object.
    """
    with open(filename, "r") as f:
        return _new_yaml().load(f)


def to_yaml_string(value: Any, key_sort: Optional[KeySort] = None) -> str:
    """
    Convert a Python object to a YAML string.
    """
    stream = StringIO()
    _new_yaml(key_sort).dump(value, stream)
    return stream.getvalue()


def write_yaml(value: Any, stream: TextIO, key_sort: Optional[KeySort] = None):
    """
    Write a Python object to a YAML stream.
    """
    _new_yaml(key_sort).dump(value, stream)


def write_yaml_file(value: Any, filename: str, key_sort: Optional[KeySort] = None):
    """
    Atomic write of the given value to the YAML file.
    """
    with atomic_output_file(filename) as f:
        with open(f, "w") as f:
            write_yaml(value, f, key_sort)


## Tests


def test_write_yaml_file_with_custom_key_sort():
    os.makedirs("tmp", exist_ok=True)

    file_path = "tmp/test_write_yaml_file.yaml"
    data = {"title": "Test Title", "author": "Test Author", "date": "2022-01-01"}

    priority_keys = ["date", "title"]
    key_sort = custom_key_sort(priority_keys)

    write_yaml_file(data, file_path, key_sort=key_sort)

    read_data = read_yaml_file(file_path)

    # Priority keys should be first.
    assert list(read_data.keys()) == priority_keys + [
        k for k in data.keys() if k not in priority_keys
    ]
