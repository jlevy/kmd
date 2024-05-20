"""
Xonsh extension for kmd.

This should make use of kmd much easier as it makes all actions available as xonsh commands.
"""

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
from typing import Callable, List
from rich import print as rprint
from rich.text import Text
from xonsh import xontribs
from kmd.config.setup import setup
from kmd.config.settings import media_cache_dir
from kmd.file_storage.workspaces import show_workspace_info
from kmd.actions.actions import run_action
from kmd.actions.registry import load_all_actions
from kmd.commands import commands
from kmd.model.actions_model import Action


setup()


class CallableAction:
    def __init__(self, action: Action):
        self.action = action

    def __call__(self, args):
        run_action(self.action, *args)
        # We don't return the result to keep the shell output clean.

    def __repr__(self):
        return f"CallableAction({repr(self.action)})"


def initialize():

    actions = load_all_actions()

    kmd_aliases = {}

    # Load all actions as xonsh commands.
    for action in actions.values():
        kmd_aliases[action.name] = CallableAction(action)

    # Additional commmands
    kmd_aliases["kmd_help"] = commands.kmd_help

    def xonsh_command_for(func: Callable):
        def command(args: List[str]):
            func(*args)

        command.__doc__ = func.__doc__
        return command

    for func in commands.all_commands():
        kmd_aliases[func.__name__] = xonsh_command_for(func)

    aliases.update(kmd_aliases)  # type: ignore

    # Conveniene to reload module.
    # TODO: Doesn't seem to reload modified Python?
    def reload() -> None:
        xontribs.xontribs_reload(["kmd"], verbose=True)

    aliases["reload"] = reload  # type: ignore


rprint(
    Text.assemble(
        ("\n🄺\n", "bright_blue"),
        ("\nWelcome to the kmd shell.\n", "bright_green"),
        "\nUse `kmd_help` for available kmd commands and actions.\n",
        "Use `xonfig tutorial` for xonsh help and `help()` for Python help.\n",
        f"Using media cache directory: {media_cache_dir()}\n",
    )
)

initialize()

try:
    show_workspace_info()
except ValueError as e:
    rprint(
        "The current directory is not a workspace. Create or switch to a workspace with the `workspace` command."
    )
print()


# TODO: Completion for actions, e.g. known URLs, resource titles, concepts, etc.
# def _action_completer(cls, prefix, line, begidx, endidx, ctx):
#     return ["https://"]
# __xonsh__.completers["foo"] = _action_completer
