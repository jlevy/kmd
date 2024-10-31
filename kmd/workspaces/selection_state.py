from pathlib import Path
from typing import Callable, List, Tuple

from kmd.config.logger import get_logger
from kmd.errors import FileNotFound, InvalidState
from kmd.file_storage.persisted_yaml import PersistedYaml
from kmd.model.paths_model import fmt_loc, StorePath
from kmd.util.format_utils import fmt_lines

log = get_logger(__name__)


class SelectionState:
    """
    A selection of items from the workspace.
    """

    def __init__(self, yaml_file: Path, exists_fn: Callable[[StorePath], bool]):
        self.selection = PersistedYaml(yaml_file, init_value=[])
        self.exists_fn = exists_fn

    def set(self, selection: List[StorePath]):
        for store_path in selection:
            if not self.exists_fn(store_path):
                raise FileNotFound(f"Selection not found: {fmt_loc(store_path)}")

        self.selection.set(selection)

    def get(self) -> List[StorePath]:
        try:
            store_paths = self.selection.read()
            filtered_store_paths = [StorePath(path) for path in store_paths if self.exists_fn(path)]
            if len(filtered_store_paths) != len(store_paths):
                log.warning(
                    "Items in selection are missing, so unselecting:\n%s",
                    fmt_lines(sorted(set(store_paths) - set(filtered_store_paths))),
                )
                self.selection.set(filtered_store_paths)
            return filtered_store_paths
        except OSError:
            raise InvalidState("No selection saved in workspace")

    def remove_values(self, targets: List[StorePath]):
        self.selection.remove_values(targets)

    def replace_values(self, replacements: List[Tuple[StorePath, StorePath]]):
        self.selection.replace_values(replacements)

    def unselect(self, unselect_paths: List[StorePath]):
        current_selection = self.get()
        new_selection = [path for path in current_selection if path not in unselect_paths]
        self.set(new_selection)
        return new_selection
