from pathlib import Path
from typing import Any, List, Tuple
from kmd.file_storage.yaml_util import read_yaml_file, write_yaml_file
from kmd.util.obj_utils import remove_values, replace_values


class PersistedYaml:
    """
    Maintain a value (such as a dictionary or list of strings) as a YAML file.
    """

    def __init__(self, filename: str | Path, value: Any):
        self.filename = str(filename)
        self.value = value

    def read(self) -> Any:
        return read_yaml_file(self.filename)

    def set(self, value: Any):
        write_yaml_file(value, self.filename)

    def remove_values(self, targets: List[Any]):
        self.value = remove_values(self.value, targets)
        self.set(self.value)

    def replace_values(self, replacements: List[Tuple[Any, Any]]):
        self.value = replace_values(self.value, replacements)
        self.set(self.value)
