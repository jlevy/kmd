"""
Xonsh extension for kmd.

This should make use of kmd much easier as it makes all actions available as xonsh commands.
"""

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from kmd.config import setup
from kmd.file_storage.file_store import show_workspace_info
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

    for func in commands.all_commands():
        kmd_aliases[func.__name__] = func

    aliases.update(kmd_aliases)  # type: ignore


print(
    "\n🄺\nWelcome to the kmd shell.\n"
    "Use `kmd_help` for available kmd commands and actions.\n"
    "Use `xonfig tutorial` for xonsh help and `help()` for Python help.\n"
)

initialize()

show_workspace_info()
print()


# TODO: Completion for actions, e.g. known URLs, resource titles, concepts, etc.
# def _action_completer(cls, prefix, line, begidx, endidx, ctx):
#     return ["https://"]
# __xonsh__.completers["foo"] = _action_completer
