"""
Xonsh extension for kmd.

This should make use of kmd much easier as it makes all actions available as xonsh commands.
"""

import time
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
from typing import Callable, List
from rich import print as rprint
from rich.text import Text
from xonsh import xontribs
from xonsh.tools import XonshError
from litellm.exceptions import APIError
from kmd.config.setup import setup
from kmd.config.settings import media_cache_dir
from kmd.config.logger import get_logger
from kmd.file_storage.workspaces import current_workspace
from kmd.actions.action_exec import run_action
from kmd.actions.action_registry import load_all_actions
from kmd.commands import commands
from kmd.model.actions_model import Action


setup()

log = get_logger(__name__)

# Common exceptions that don't merit a full stack trace.
# Might not want this for
_common_exceptions = (ValueError, IOError, XonshError, APIError)


def _elide_traceback(exception_str: str) -> str:
    lines = exception_str.splitlines()
    return "\n".join(
        [
            line
            for line in lines
            if line.strip()
            and not line.lstrip().startswith("Traceback")
            and not line.lstrip().startswith("File ")
            and not line.lstrip().startswith("The above exception")
            and not line.startswith("    ")
        ]
        + ["See log for more details."]
    )


class CallableAction:
    def __init__(self, action: Action):
        self.action = action

    def __call__(self, args):
        start_time = time.time()
        try:
            run_action(self.action, *args)
            # We don't return the result to keep the shell output clean.
        except _common_exceptions as e:
            rprint(Text(f"Action error: {_elide_traceback(str(e))}", "bright_red"))
            log.info("Action error: %s", e)
        finally:
            end_time = time.time()
            elapsed = end_time - start_time
            if elapsed > 5.0:
                log.message("⏱️ Action %s took %.1fs.", self.action.name, elapsed)

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
            try:
                func(*args)
            except _common_exceptions as e:
                rprint(Text(f"Command error: {_elide_traceback(str(e))}", "bright_red"))
                log.info("Command error: %s", e)

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
        ("\nWelcome to kmd.\n", "bright_green"),
        "\nUse `kmd_help` for available kmd commands and actions.\n",
        "Use `xonfig tutorial` for xonsh help and `help()` for Python help.\n",
        f"Using media cache directory: {media_cache_dir()}\n",
    )
    # TODO: Replace help() with kmd_help.
)

initialize()

try:
    current_workspace()
except ValueError as e:
    rprint(
        "The current directory is not a workspace. Create or switch to a workspace with the `workspace` command."
    )
print()


# TODO: Completion for actions, e.g. known URLs, resource titles, concepts, parameters and values, etc.
# def _action_completer(cls, prefix, line, begidx, endidx, ctx):
#     return ["https://"]
# __xonsh__.completers["foo"] = _action_completer
