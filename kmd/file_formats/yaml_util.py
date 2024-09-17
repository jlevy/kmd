"""
YAML file storage.
"""

import os
from io import StringIO
from typing import Any, Callable, List, Optional, TextIO

from ruamel.yaml import YAML
from strif import atomic_output_file

from kmd.model.paths_model import StorePath

KeySort = Callable[[str], tuple]


def none_or_empty_dict(val: Any) -> bool:
    return val is None or val == {}


def new_yaml(
    key_sort: Optional[KeySort] = None,
    suppress_vals: Optional[Callable[[Any], bool]] = none_or_empty_dict,
    stringify_unknown: bool = False,
) -> YAML:
    """
    Configure a new YAML instance with custom settings.

    If just using this for pretty-printing values, can set `stringify_unknown` to avoid
    RepresenterError for unexpected types.
    """
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False  # Block style dictionaries.

    suppr = suppress_vals or (lambda v: False)

    # Ignore None values in output. Sort keys if key_sort is provided.
    def represent_dict(dumper, data):
        if key_sort:
            data = {k: data[k] for k in sorted(data.keys(), key=key_sort)}
        return dumper.represent_dict({k: v for k, v in data.items() if not suppr(v)})

    yaml.representer.add_representer(dict, represent_dict)

    # Our StorePath is just a str.
    def represent_store_path(dumper, data):
        return dumper.represent_str(str(data))

    yaml.representer.add_representer(StorePath, represent_store_path)

    if stringify_unknown:

        def represent_unknown(dumper, data):
            return dumper.represent_str(str(data))

        yaml.representer.add_representer(None, represent_unknown)

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
    return new_yaml().load(yaml_string)


def read_yaml_file(filename: str) -> Any:
    """
    Read YAML file into a Python object.
    """
    with open(filename, "r") as f:
        return new_yaml().load(f)


def to_yaml_string(
    value: Any, key_sort: Optional[KeySort] = None, stringify_unknown: bool = False
) -> str:
    """
    Convert a Python object to a YAML string.
    """
    stream = StringIO()
    new_yaml(key_sort, stringify_unknown=stringify_unknown).dump(value, stream)
    return stream.getvalue()


def write_yaml(
    value: Any, stream: TextIO, key_sort: Optional[KeySort] = None, stringify_unknown: bool = False
):
    """
    Write a Python object to a YAML stream.
    """
    new_yaml(key_sort, stringify_unknown=stringify_unknown).dump(value, stream)


def write_yaml_file(
    value: Any, filename: str, key_sort: Optional[KeySort] = None, stringify_unknown: bool = False
):
    """
    Atomic write of the given value to the YAML file.
    """
    with atomic_output_file(filename) as f:
        with open(f, "w") as f:
            write_yaml(value, f, key_sort, stringify_unknown=stringify_unknown)


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


def test_write_yaml_file_with_suppress_vals():
    os.makedirs("tmp", exist_ok=True)

    file_path = "tmp/test_write_yaml_file_suppress_vals.yaml"
    data = {
        "title": "Test Title",
        "author": "Test Author",
        "date": "2022-01-01",
        "empty_dict": {},
        "none_value": None,
        "content": "Some content",
    }

    write_yaml_file(data, file_path)

    read_data = read_yaml_file(file_path)

    assert "empty_dict" not in read_data
    assert "none_value" not in read_data

    assert read_data["title"] == "Test Title"
    assert read_data["author"] == "Test Author"
    assert read_data["date"] == "2022-01-01"
    assert read_data["content"] == "Some content"
