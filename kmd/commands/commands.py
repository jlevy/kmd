import logging
import os
from textwrap import indent
from kmd.config import WS_SUFFIX
from kmd.file_storage.file_store import show_workspace_info

log = logging.getLogger(__name__)


_commands = []


def register_command(func):
    _commands.append(func)
    return func

def all_commands():
    return _commands

@register_command
def kmd_help():
    """
    kmd help. Lists all available actions.
    """
    from kmd.actions.registry import load_all_actions

    print("\nAvailable kmd commands:\n")
    for command in _commands:
        print(f"{command.__name__}:\n{indent(command.__doc__.strip(), prefix='    ')}\n")

    print("\nAvailable kmd actions:\n")
    actions = load_all_actions()
    for action in actions.values():
        print(
            f"{action.name} - {action.friendly_name}:\n{indent(action.description, prefix="    ")}\n"
        )


@register_command
def new_workspace(workspace_name: str) -> str:
    """
    Create a new workspace.
    """

    if not workspace_name.endswith(WS_SUFFIX):
        workspace_name = f"{workspace_name}{WS_SUFFIX}"

    os.makedirs(workspace_name, exist_ok=True)

    log.warning("Created new workspace: %s", workspace_name)

    # TODO: Change cwd within xonsh.

    return workspace_name


@register_command
def show_workspace():
    """
    Show the current workspace.
    """
    show_workspace_info()
