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
import re
from typing import Dict, Iterable, List, Tuple
from xonsh.completers.tools import contextual_completer, CompletionContext, CompleterResult
from xonsh.completers.completer import add_one_completer, RichCompletion
from kmd.commands.command_registry import CommandFunction, all_commands, kmd_command
from kmd.config.setup import setup
from kmd.config.logger import get_logger
from kmd.config.text_styles import (
    COLOR_ACTION_TEXT,
    COLOR_COMMAND_TEXT,
    EMOJI_ACTION,
    EMOJI_WARN,
    PROMPT_COLOR_NORMAL,
    PROMPT_COLOR_WARN,
    PROMPT_MAIN,
)
from kmd.model.actions_model import Action
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_checks import (
    items_matching_precondition,
)
from kmd.shell_tools.action_wrapper import ShellCallableAction
from kmd.shell_tools.function_inspect import ParamInfo
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

    # Override default ? command.
    kmd_commands["?"] = "assist"

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


def _completion_match(query: str, values: Iterable[str]) -> List[str]:
    """
    Match a prefix against a list of items and return prefix matches and substring matches.
    """
    options = [(value.lower().strip(), value) for value in values]
    query = query.lower().strip()

    prefix_matches = [value for (norm_value, value) in options if norm_value.startswith(query)]
    substring_matches = [value for (norm_value, value) in options if query in norm_value]
    return prefix_matches + substring_matches


@contextual_completer
def command_or_action_completer(context: CompletionContext) -> CompleterResult:
    """
    Completes command names. We don't complete on regular shell commands to keep it cleaner.
    """

    if context.command and context.command.arg_index == 0:
        prefix = context.command.prefix

        command_matches = _completion_match(prefix, [c.__name__ for c in _commands.values()])
        command_completions = [
            RichCompletion(
                name,
                description=single_line(_commands[name].__doc__ or ""),
                style=COLOR_COMMAND_TEXT,
            )
            for name in command_matches
        ]

        action_matches = _completion_match(prefix, [a.name for a in _actions.values()])
        action_completions = [
            RichCompletion(
                name,
                display=f"{name} {EMOJI_ACTION}",
                description=single_line(_actions[name].description or ""),
                style=COLOR_ACTION_TEXT,
                append_space=True,
            )
            for name in action_matches
        ]

        def completion_sort(completion: RichCompletion) -> Tuple[int, str]:
            return (len(completion.value), completion.value)

        completions = sorted(command_completions + action_completions, key=completion_sort)

        # Tab on an empty line also suggests help.
        if prefix.strip() == "":
            help_completion = RichCompletion("?", description="Ask a question to get help.")
            completions = [help_completion] + completions

        return set(completions)


@contextual_completer
def item_completer(context: CompletionContext) -> CompleterResult:
    """
    If the current command is an action, complete with paths that match the precondition
    for that action.
    """

    try:
        if context.command and context.command.arg_index >= 1:
            action_name = context.command.args[0].value
            action = _actions.get(action_name)

            prefix = context.command.prefix

            is_prefix_match = Precondition(
                lambda item: bool(item.store_path and item.store_path.startswith(prefix))
            )

            if action and action.precondition:
                ws = current_workspace()
                match_precondition = action.precondition & is_prefix_match
                matching_items = list(
                    items_matching_precondition(ws, match_precondition, max_results=MAX_COMPLETIONS)
                )
                # Too many matches is not so useful.
                if len(matching_items) < MAX_COMPLETIONS:
                    return {
                        RichCompletion(
                            str(item.store_path),
                            display=f"{item.store_path} ({action.precondition.name}) ",
                            description=item.title or "",
                            append_space=True,
                        )
                        for item in matching_items
                        if item.store_path and item.store_path.startswith(prefix)
                    }
    except InvalidStoreState:
        return


@contextual_completer
def help_question_completer(context: CompletionContext) -> CompleterResult:
    """
    Suggest help questions after a `?` on the command line.
    """
    if context.command:
        command = context.command
        arg_index = context.command.arg_index
        prefix = context.command.prefix.lstrip()

        # ?some question
        # ? some question
        if (arg_index == 0 and prefix.startswith("?")) or (
            arg_index == 1 and command.args[0].value == "?"
        ):
            query = prefix.lstrip("? ")

            # Extract questions from the FAQ.
            from kmd.docs.topics.faq import __doc__ as faq_doc

            questions = re.findall(r"^#+ (.+\?)\s*$", faq_doc, re.MULTILINE)
            assert len(questions) > 2

            return {RichCompletion(question) for question in _completion_match(query, questions)}


@contextual_completer
def options_completer(context: CompletionContext) -> CompleterResult:
    """
    Suggest options completions after a `-` or `--` on the command line.
    """
    if context.command and context.command.arg_index > 0:
        prefix = context.command.prefix

        if prefix.startswith("-"):
            command_name = context.command.args[0].value

            command = _commands.get(command_name)
            action = _actions.get(command_name)

            if command:
                param_info: ParamInfo | None = getattr(command, "__param_info__", None)
                if param_info:
                    _pos_params, _kw_params, kw_docs = param_info
                    completions = [
                        RichCompletion(
                            param.shell_prefix(),
                            description=param.description or "",
                            append_space=True,
                        )
                        for param in kw_docs
                        if param.shell_prefix().startswith(prefix)
                    ]
                    if "--help".startswith(prefix):
                        completions.append(
                            RichCompletion("--help", description="Show more help for this command.")
                        )
                    return set(completions)

            if action:
                param_docs = action.params()
                completions = [
                    RichCompletion(
                        param.shell_prefix(), description=param.description or "", append_space=True
                    )
                    for param in param_docs
                    if param.shell_prefix().startswith(prefix)
                ]
                if "--help".startswith(prefix):
                    completions.append(
                        RichCompletion("--help", description="Show more help for this action.")
                    )
                return set(completions)


def _kmd_xonsh_prompt():
    from kmd.file_storage.workspaces import current_workspace_name

    name = current_workspace_name()
    workspace_str = (
        f"{{{PROMPT_COLOR_NORMAL}}}" + name if name else f"{{{PROMPT_COLOR_WARN}}}(no workspace)"
    )
    return f"{workspace_str} {{{PROMPT_COLOR_NORMAL}}}{PROMPT_MAIN}{{RESET}} "


def shell_setup():
    add_one_completer("command_or_action_completer", command_or_action_completer, "start")
    add_one_completer("item_completer", item_completer, "start")
    add_one_completer("help_question_completer", help_question_completer, "start")
    add_one_completer("options_completer", options_completer, "start")

    __xonsh__.env["PROMPT"] = _kmd_xonsh_prompt  # type: ignore  # noqa: F821


# Startup:

if _is_interactive:
    welcome()

initialize()

post_initialize()

shell_setup()
