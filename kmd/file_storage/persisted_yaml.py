from pathlib import Path
from typing import Any, List, Tuple
from kmd.file_storage.yaml_util import read_yaml_file, write_yaml_file
from kmd.util.obj_utils import remove_values, replace_values


class PersistedYaml:
    """
    Maintain simple data (such as a dictionary or list of strings) as a YAML file.
    File writes are atomic but does not lock.
    """

    def __init__(self, filename: str | Path, value: Any):
        self.filename = str(filename)
        self.set(value)

    def read(self) -> Any:
        return read_yaml_file(self.filename)

    def set(self, value: Any):
        write_yaml_file(value, self.filename)

    def remove_values(self, targets: List[Any]):
        value = self.read()
        new_value = remove_values(value, targets)
        self.set(new_value)

    def replace_values(self, replacements: List[Tuple[Any, Any]]):
        value = self.read()
        new_value = replace_values(value, replacements)
        self.set(new_value)
