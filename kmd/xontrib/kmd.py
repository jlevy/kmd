"""
Xonsh extension for kmd.

Sets up all commands and actions for use in xonsh. This makes using kmd far easier
for interactive use than from a regular shell command line.

Can run from the custom kmd shell (main.py) or from a regular xonsh shell.
"""

import importlib
import os
import runpy
import threading
import time
from typing import Dict
from xonsh.completers.tools import contextual_completer, CompletionContext, CompleterResult
from xonsh.completers.completer import add_one_completer, RichCompletion
from kmd.commands.command_registry import CommandFunction, all_commands, kmd_command
from kmd.config.setup import setup
from kmd.config.logger import get_logger
from kmd.config.text_styles import (
    COLOR_ACTION,
    COLOR_COMMAND,
    EMOJI_ACTION,
    EMOJI_WARN,
    PROMPT_COLOR_NORMAL,
    PROMPT_COLOR_WARN,
)
from kmd.model.actions_model import Action
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_checks import (
    items_matching_precondition,
)
from kmd.shell_tools.action_wrapper import ShellCallableAction
from kmd.shell_tools.function_wrapper import wrap_for_shell_args
from kmd.text_formatting.text_formatting import single_line
from kmd.text_ui.command_output import output
from kmd.file_storage.workspaces import current_workspace
from kmd.action_defs import reload_all_actions
from kmd.commands import commands
from kmd.commands.commands import welcome
from kmd.model.errors_model import InvalidStoreState
from kmd.shell_tools.exception_printing import wrap_with_exception_printing

setup()  # Call to config logging before anything else.

log = get_logger(__name__)

_commands: Dict[str, CommandFunction] = {}
_actions: Dict[str, Action] = {}
_is_interactive = __xonsh__.env["XONSH_INTERACTIVE"]  # type: ignore  # noqa: F821


MAX_COMPLETIONS = 500


# We add action loading here direcctly in the xontrib so we can update the aliases.
@kmd_command
def load(*paths: str) -> None:
    """
    Load kmd Python extensions. Simply imports and the defined actions should use
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

    global _commands
    _commands = all_commands()

    for func in _commands.values():
        kmd_commands[func.__name__] = wrap_with_exception_printing(wrap_for_shell_args(func))

    aliases.update(kmd_commands)  # type: ignore  # noqa: F821


def load_xonsh_actions():
    kmd_actions = {}

    # Load all actions as xonsh commands.
    global _actions
    _actions = reload_all_actions()

    for action in _actions.values():
        kmd_actions[action.name] = ShellCallableAction(action)

    aliases.update(kmd_actions)  # type: ignore  # noqa: F821


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


@contextual_completer
def command_or_action_completer(context: CompletionContext) -> CompleterResult:
    """
    Completes command names. We don't complete on regular shell commands to keep it cleaner.
    """
    if context.command and context.command.arg_index == 0:
        command_completions = {
            RichCompletion(
                c.__name__, description=single_line(c.__doc__ or ""), style=COLOR_COMMAND
            )
            for c in _commands.values()
            if c.__name__.startswith(context.command.prefix)
        }
        action_completions = {
            RichCompletion(
                a.name,
                display=f"{a.name} {EMOJI_ACTION}",
                description=single_line(a.description or ""),
                style=COLOR_ACTION,
            )
            for a in _actions.values()
            if a.name.startswith(context.command.prefix)
        }
        return command_completions | action_completions


@contextual_completer
def item_completer(context: CompletionContext) -> CompleterResult:
    """
    If the current command is an action, complete with paths that match the precondition
    for that action.
    """
    if context.command and context.command.arg_index >= 1:
        action_name = context.command.args[0].value
        action = _actions.get(action_name)

        prefix = context.command.prefix
        matches_prefix = Precondition(
            lambda item: bool(item.store_path and item.store_path.startswith(prefix))
        )

        if action and action.precondition:
            ws = current_workspace()
            match_precondition = action.precondition & matches_prefix
            matching_items = list(
                items_matching_precondition(ws, match_precondition, max_results=MAX_COMPLETIONS)
            )
            # Too many matches is just not useful.
            if len(matching_items) < MAX_COMPLETIONS:
                return {
                    RichCompletion(
                        str(item.store_path),
                        display=f"{item.store_path} ({action.precondition.name}) ",
                        description=item.title or "",
                    )
                    for item in matching_items
                    if item.store_path and item.store_path.startswith(context.command.prefix)
                }


def _kmd_xonsh_prompt():
    from kmd.file_storage.workspaces import current_workspace_name

    name = current_workspace_name()
    workspace_str = (
        f"{{{PROMPT_COLOR_NORMAL}}}" + name if name else f"{{{PROMPT_COLOR_WARN}}}(no workspace)"
    )
    return f"{workspace_str} {{{PROMPT_COLOR_NORMAL}}}❯{{RESET}} "


def shell_setup():
    add_one_completer("command_or_action_completer", command_or_action_completer, "start")
    add_one_completer("item_completer", item_completer, "start")

    __xonsh__.env["PROMPT"] = _kmd_xonsh_prompt  # type: ignore  # noqa: F821


# Startup:

if _is_interactive:
    welcome()

initialize()

post_initialize()

shell_setup()
