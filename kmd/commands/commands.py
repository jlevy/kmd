import logging
import os
from textwrap import indent
from typing import Callable, List, Optional, Tuple
from kmd.config import WS_SUFFIX
from kmd.file_storage.file_store import show_workspace_info
from kmd.util.view_file import view_file
from kmd.util.text_formatting import format_lines, plural
from kmd.file_storage.file_store import current_workspace

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


def _canon_workspace_name(name: str) -> Tuple[str, str]:
    name = name.strip()
    workspace_name = name.removesuffix(WS_SUFFIX)
    workspace_dir = name if name.endswith(WS_SUFFIX) else f"{name}{WS_SUFFIX}"
    return workspace_name, workspace_dir


@register_command
def workspace(workspace_name: Optional[str] = None) -> None:
    """
    Show info on the current workspace.
    """
    if workspace_name:
        ws_name, ws_dir = _canon_workspace_name(workspace_name)
        os.makedirs(ws_dir, exist_ok=True)
        os.chdir(ws_dir)
        log.warning("Changed to workspace: %s", ws_name)
    show_workspace_info()


@register_command
def selection() -> None:
    """
    Show the current selection.
    """

    selection = current_workspace().get_selection()
    if not selection:
        log.warning("No selection.")
    else:
        log.warning(
            "Selected %s %s:\n%s",
            len(selection),
            plural("item", len(selection)),
            format_lines(selection),
        )


@register_command
def show(path: Optional[str] = None) -> None:
    """
    Show the contents of a file.
    """
    if path:
        view_file(path)
    else:
        selection = current_workspace().get_selection()
        if not selection:
            raise ValueError("No selection")
        view_file(selection[0])
