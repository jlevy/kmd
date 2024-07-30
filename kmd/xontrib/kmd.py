"""
Xonsh extension for kmd.

Sets up all commands and actions for use in xonsh. This makes using kmd far easier
for interactive use than from a regular shell command line.

Can run from the custom kmd shell (main.py) or from a regular xonsh shell.
"""

import importlib
import os
import runpy
from textwrap import dedent
import threading
import time
from typing import Callable, List
from rich import get_console
from xonsh.tools import XonshError
import litellm
from kmd.config.setup import setup
from kmd.config.settings import cache_dir
from kmd.config.logger import get_logger
from kmd.config.text_styles import (
    EMOJI_WARN,
    COLOR_ERROR,
    COLOR_HEADING,
    COLOR_LOGO,
    LOGO,
    PROMPT_COLOR_NORMAL,
    PROMPT_COLOR_WARN,
    SPINNER,
)
from kmd.text_ui.command_output import Wrap, output
from kmd.file_storage.workspaces import current_workspace
from kmd.action_defs import reload_all_actions
from kmd.action_exec.action_exec import run_action
from kmd.commands import commands
from kmd.commands.commands import kmd_command
from kmd.model.actions_model import Action
from kmd.model.errors_model import SelfExplanatoryError, InvalidStoreState
from kmd.util.log_calls import log_tallies

setup()

log = get_logger(__name__)

# Common exceptions that don't merit a full stack trace.
_common_exceptions = (SelfExplanatoryError, IOError, XonshError, litellm.exceptions.APIError)


def _summarize_traceback(exception: Exception) -> str:
    exception_str = str(exception)
    lines = exception_str.splitlines()
    exc_type = type(exception).__name__
    return f"{exc_type}: " + "\n".join(
        [
            line
            for line in lines
            if line.strip() and not line.lstrip().startswith("Traceback")
            # and not line.lstrip().startswith("File ")
            and not line.lstrip().startswith("The above exception") and not line.startswith("    ")
        ]
        + ["Run `logs` for details."]
    )


def xonsh_command_for(func: Callable):
    def command(args: List[str]):
        try:
            func(*args)
        except _common_exceptions as e:
            log.error(f"[{COLOR_ERROR}]Command error:[/{COLOR_ERROR}] %s", _summarize_traceback(e))

            log.info("Command error details: %s", e, exc_info=True)
        finally:
            output()

    command.__doc__ = func.__doc__
    return command


class CallableAction:
    def __init__(self, action: Action):
        self.action = action

    def __call__(self, args):
        try:
            if not self.action.interactive_input:
                with get_console().status(f"Running action {self.action.name}…", spinner=SPINNER):
                    run_action(self.action, *args)
            else:
                run_action(self.action, *args)
            # We don't return the result to keep the xonsh shell output clean.
        except _common_exceptions as e:
            log.error(f"[{COLOR_ERROR}]Action error:[/{COLOR_ERROR}] %s", _summarize_traceback(e))
            log.info("Action error details: %s", e, exc_info=True)
        finally:
            log_tallies(if_slower_than=10.0)
            output()
            output()

    def __repr__(self):
        return f"CallableAction({str(self.action)})"


# We add action loading here direcctly in the xontrib so we can update the aliases.
@kmd_command
def load(*paths: str) -> None:
    """
    Load Python extensions into kmd. Simply imports and the defined actions should use
    @kmd_action to register themselves.
    """
    for path in paths:
        if os.path.isfile(path) and path.endswith(".py"):
            runpy.run_path(path, run_name="__main__")
        else:
            importlib.import_module(path)

    # Now reload all actions into the environment so the new action is visible.
    reload_all_actions()
    load_xonsh_actions()

    log.message("Imported extensions and reloaded actions: %s", ", ".join(paths))
    # TODO: Track and expose to the user which extensions are loaded.


def load_xonsh_commands():
    kmd_commands = {}

    # kmd command aliases in xonsh.
    kmd_commands["kmd_help"] = commands.kmd_help
    kmd_commands["load"] = load

    # TODO: Figure out how to get this to work:
    # aliases["py_help"] = help
    # aliases["help"] = commands.kmd_help

    # TODO: Doesn't seem to reload modified Python?
    # def reload() -> None:
    #     xontribs.xontribs_reload(["kmd"], verbose=True)
    #
    # aliases["reload"] = reload  # type: ignore

    for func in commands.all_commands():
        kmd_commands[func.__name__] = xonsh_command_for(func)

    aliases.update(kmd_commands)  # type: ignore  # noqa: F821


def load_xonsh_actions():
    kmd_actions = {}
    # Load all actions as xonsh commands.
    actions = reload_all_actions()

    for action in actions.values():
        kmd_actions[action.name] = CallableAction(action)

    aliases.update(kmd_actions)  # type: ignore  # noqa: F821


_is_interactive = __xonsh__.env["XONSH_INTERACTIVE"]  # type: ignore  # noqa: F821


def welcome():
    if _is_interactive:
        output()
        output(LOGO, color=COLOR_LOGO)
        output()
        output("Welcome to kmd.\n", color=COLOR_HEADING)
        output()
        # output(f"\n{len(kmd_commands)} commands and {len(kmd_actions)} actions are available.")
        output(
            dedent(
                """
                Use `kmd_help` for help. Or simply ask a question about kmd or what you want to do.
                Any question (ending in ?) on the command line invokes the kmd assistant.
                """
            ).strip(),
            text_wrap=Wrap.WRAP_FULL,
        )


def initialize():
    if _is_interactive:
        # Try to seem a little faster starting up.
        def load():
            load_start_time = time.time()

            load_xonsh_commands()
            load_xonsh_actions()

            load_time = time.time() - load_start_time
            log.info(f"Action and command loading took {load_time:.2f}s.")

        load_thread = threading.Thread(target=load)
        load_thread.start()

        output()
        log.message("Using cache directory: %s", cache_dir())
    else:
        load_xonsh_commands()
        load_xonsh_actions()


def post_initialize():
    if _is_interactive:
        try:
            current_workspace().log_store_info()  # Validates and logs info for user.
        except InvalidStoreState:
            output(
                f"{EMOJI_WARN} The current directory is not a workspace. "
                "Create or switch to a workspace with the `workspace` command."
            )
        output()


welcome()

initialize()

post_initialize()


# TODO: Completion for action and command args, e.g. known URLs, resource titles, concepts, parameters and values, etc.
# def _action_completer(cls, prefix, line, begidx, endidx, ctx):
#     return ["https://"]
# __xonsh__.completers["foo"] = _action_completer


def _kmd_xonsh_prompt():
    from kmd.file_storage.workspaces import current_workspace_name

    name = current_workspace_name()
    workspace_str = (
        f"{{{PROMPT_COLOR_NORMAL}}}" + name if name else f"{{{PROMPT_COLOR_WARN}}}(no workspace)"
    )
    return f"{workspace_str} {{{PROMPT_COLOR_NORMAL}}}❯{{RESET}} "


__xonsh__.env["PROMPT"] = _kmd_xonsh_prompt  # type: ignore  # noqa: F821
