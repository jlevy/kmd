from pathlib import Path
from typing import cast, List, Optional, Sequence, Tuple

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput, MissingInput
from kmd.file_storage.workspaces import current_workspace
from kmd.model.paths_model import InputArg, StorePath

log = get_logger(__name__)


def resolve_path_arg(path_str: str) -> Path | StorePath:
    """
    Resolve a path argument to a Path or StorePath, if it is within the current workspace.
    """
    path = Path(path_str)
    if path.is_absolute():
        return path
    elif store_path := current_workspace().resolve_path(path):
        return store_path
    else:
        return path


def assemble_path_args(*paths: Optional[str]) -> List[StorePath | Path]:
    """
    Assemble paths or store paths from the current workspace, or the current selection if
    no paths are given.
    """
    resolved = [resolve_path_arg(path) for path in paths if path]
    if not resolved:
        ws = current_workspace()
        resolved = ws.get_selection()
        if not resolved:
            raise MissingInput("No selection")
    return cast(List[StorePath | Path], resolved)


# TODO: Get more commands to work on files outside the workspace by importing them first.
def _check_store_paths(paths: Sequence[StorePath | Path]) -> List[StorePath]:
    """
    Check that all paths are store paths.
    """
    ws = current_workspace()
    for path in paths:
        if not ws.exists(StorePath(path)):
            raise InvalidInput(f"Store path not found: {path}")
    return [StorePath(str(path)) for path in paths]


def assemble_store_path_args(*paths: Optional[str]) -> List[StorePath]:
    """
    Assemble store paths from the current workspace.
    """
    return _check_store_paths(assemble_path_args(*paths))


def assemble_action_args(*paths: Optional[str]) -> Tuple[List[InputArg], bool]:
    """
    Assemble args for an action.
    """
    resolved = [resolve_path_arg(path) for path in paths if path]
    if not resolved:
        try:
            selection_args = current_workspace().get_selection()
            return cast(List[InputArg], selection_args), True
        except MissingInput:
            return [], False
    else:
        return cast(List[InputArg], resolved), False
