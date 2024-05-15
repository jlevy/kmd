import logging
import os
from textwrap import indent
from typing import Callable, List, Optional
from kmd.config import WS_SUFFIX
from kmd.file_storage.file_store import show_workspace_info
from kmd.util.text_formatting import format_lines, plural

log = logging.getLogger(__name__)


_commands: List[Callable] = []


def register_command(func):
    _commands.append(func)
    return func


def all_commands():
    return _commands


@register_command
def kmd_help() -> None:
    """
    kmd help. Lists all available actions.
    """
    from kmd.actions.registry import load_all_actions

    print("\nAvailable kmd commands:\n")

    def format_doc(doc: Optional[str]) -> str:
        return indent(doc.strip(), prefix="    ") if doc else ""

    for command in _commands:
        print(f"{command.__name__}:\n{format_doc(command.__doc__)}\n")

    print("\nAvailable kmd actions:\n")
    actions = load_all_actions()
    for action in actions.values():
        print(f"{action.name}:\n{indent(action.description, prefix="    ")}\n")


@register_command
def new_workspace(workspace_name: str) -> None:
    """
    Create a new workspace.
    """

    if not workspace_name.endswith(WS_SUFFIX):
        workspace_name = f"{workspace_name}{WS_SUFFIX}"

    os.makedirs(workspace_name, exist_ok=True)

    log.warning("Created new workspace: %s", workspace_name)

    # TODO: Change cwd within xonsh.


@register_command
def workspace() -> None:
    """
    Show info on the current workspace.
    """
    show_workspace_info()


@register_command
def selection() -> None:
    """
    Show the current selection.
    """
    from kmd.file_storage.file_store import current_workspace

    workspace = current_workspace()
    selection = workspace.get_selection()
    if not selection:
        log.warning("No selection.")
    else:
        log.warning(
            "Selected %s %s:\n%s",
            len(selection),
            plural("item", len(selection)),
            format_lines(selection),
        )
