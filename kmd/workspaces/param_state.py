from pathlib import Path

from kmd.file_storage.persisted_yaml import PersistedYaml
from kmd.model.params_model import ParamValues


class ParamState:
    """
    Persist global parameters for a workspace.
    """

    def __init__(self, yaml_file: Path):
        self.params = PersistedYaml(yaml_file, init_value={})

    def set(self, action_params: dict):
        """Set a global parameter for this workspace."""
        self.params.save(action_params)

    def get_values(self) -> ParamValues:
        """Get any parameters set globally for this workspace."""
        try:
            return ParamValues(self.params.read())
        except OSError:
            return ParamValues({})
