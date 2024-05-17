import logging
import os
import re
import textwrap
from typing import Callable, List, Optional
from rich import print as rprint
from rich.text import Text
from kmd.commands.local_file_tools import open_platform_specific

from kmd.file_storage.workspaces import canon_workspace_name, current_workspace, show_workspace_info
from kmd.model.locators import StorePath
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

    rprint(Text("\nAvailable kmd commands:\n", style="bright_green"))

    def format_doc(name: str, doc: str) -> Text:
        wrapped = textwrap.fill(doc, width=70, initial_indent="", subsequent_indent="    ")
        return Text.assemble((name, "bright_blue"), (": ", "bright_blue"), (wrapped, "default"))

    for command in _commands:
        doc = command.__doc__ if command.__doc__ else ""
        rprint(format_doc(command.__name__, doc.strip()))
        rprint()

    rprint(Text("\nAvailable kmd actions:\n", style="bright_green"))
    actions = load_all_actions()
    for action in actions.values():
        rprint(format_doc(action.name, action.description))
        rprint()


@register_command
def workspace(workspace_name: Optional[str] = None) -> None:
    """
    Show info on the current workspace.
    """
    if workspace_name:
        ws_name, ws_dir = canon_workspace_name(workspace_name)
        if not re.match(r"^\w+$", ws_name):
            raise ValueError(
                "Use an alphanumeric name (no spaces or special characters) for the workspace"
            )
        os.makedirs(ws_dir, exist_ok=True)
        os.chdir(ws_dir)
        log.warning("Changed to workspace: %s", ws_name)
    show_workspace_info()


@register_command
def select() -> None:
    """
    Get or show the current selection.
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
        open_platform_specific(path)
    else:
        selection = current_workspace().get_selection()
        if not selection:
            raise ValueError("No selection")
        open_platform_specific(selection[0])


@register_command
def archive(path: StorePath) -> None:
    """
    Archive the item at the given path.
    """
    current_workspace().archive(path)
    log.warning("Archived %s", path)


@register_command
def unarchive(path: StorePath) -> None:
    """
    Unarchive the item at the given path.
    """
    store_path = current_workspace().unarchive(path)
    log.warning("Unarchived %s", store_path)
