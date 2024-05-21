"""
YAML file storage.
"""

from io import StringIO
from typing import Any, TextIO
from ruamel.yaml import YAML
from strif import atomic_output_file


def _new_yaml() -> YAML:
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False  # Block style dictionaries.
    return yaml


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


def to_yaml_string(value: Any) -> str:
    """
    Convert a Python object to a YAML string.
    """
    stream = StringIO()
    _new_yaml().dump(value, stream)
    return stream.getvalue()


def write_yaml(value: Any, stream: TextIO):
    """
    Write a Python object to a YAML stream.
    """
    _new_yaml().dump(value, stream)


def write_yaml_file(value: Any, filename: str):
    """
    Atomic write of the given value to the YAML file.
    """
    with atomic_output_file(filename) as f:
        with open(f, "w") as f:
            write_yaml(value, f)
