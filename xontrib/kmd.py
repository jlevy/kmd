"""
Xonsh extension for kmd.

This should make use of kmd much easier as it makes all actions available as xonsh commands.
"""

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from kmd.actions.actions import run_action
from kmd.actions.registry import load_all_actions
from kmd.commands import commands
from kmd.config import setup
from kmd.model.actions_model import Action


setup()

actions = load_all_actions()

kmd_aliases = {}


class CallableAction:
    def __init__(self, action: Action):
        self.action = action

    def __call__(self, args):
        return run_action(self.action, *args)

    def __repr__(self):
        return f"CallableAction({repr(self.action)})"


# Load all actions as xonsh commands.
for action in actions.values():
    kmd_aliases[action.name] = CallableAction(action)

kmd_aliases["list_actions"] = commands.list_actions

aliases.update(kmd_aliases)  # type: ignore

print(
    "\n🄺\nkmd is loaded.\n"
    "Use `list_actions` for available kmd actions.\n"
    "Use `xonfig tutorial` for xonsh help and `help()` for Python help.\n"
)


# TODO: Completion for actions, e.g. known URLs, resource titles, concepts, etc.
# def _action_completer(cls, prefix, line, begidx, endidx, ctx):
#     return ["https://"]
# __xonsh__.completers["foo"] = _action_completer
