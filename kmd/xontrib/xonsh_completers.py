from typing import cast, Iterable, List, Tuple

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from xonsh.completers.completer import add_one_completer, RichCompletion
from xonsh.completers.tools import CompleterResult, CompletionContext, contextual_completer

from kmd.commands.help_commands import HELP_COMMANDS
from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_ACTION_TEXT, COLOR_COMMAND_TEXT, EMOJI_TASK
from kmd.docs.faq_headings import faq_headings
from kmd.errors import InvalidState
from kmd.file_storage.workspaces import current_workspace
from kmd.help.function_param_info import annotate_param_info
from kmd.model.params_model import Param
from kmd.model.paths_model import fmt_store_path
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_checks import items_matching_precondition
from kmd.util.format_utils import single_line
from kmd.util.log_calls import log_calls

log = get_logger(__name__)

MAX_COMPLETIONS = 200

# We want to keep completion fast, so make it obvious when it's slow.
SLOW_COMPLETION = 0.15


def _completion_match(
    query: str, values: Iterable[str | RichCompletion]
) -> List[str | RichCompletion]:
    """
    Match a prefix against a list of items and return prefix matches and substring matches.
    """
    options = [(value.lower().strip(), value) for value in values]
    query = query.lower().strip()

    prefix_matches = [value for (norm_value, value) in options if norm_value.startswith(query)]
    substring_matches = [value for (norm_value, value) in options if query in norm_value]
    return prefix_matches + substring_matches


def _path_prefix_match(prefix: str, path_str: str) -> bool:
    return path_str.startswith(prefix)


def _all_help_completions(include_bare_qm: bool) -> List[RichCompletion]:
    questions = ["? " + question for question in faq_headings()]
    possible_completions = questions + HELP_COMMANDS
    if include_bare_qm:
        help_completion = RichCompletion("?", description="Ask a question to get help.")
        possible_completions.insert(0, help_completion)
    return [
        RichCompletion(question, display=question.lstrip("? ")) for question in possible_completions
    ]


def _item_completions(
    prefix: str,
    precondition: Precondition = Precondition.always,
    complete_from_sandbox: bool = False,
) -> CompleterResult:
    prefix = prefix.lstrip("@")

    ws = current_workspace()
    if ws.is_sandbox and not complete_from_sandbox:
        return None

    is_prefix_match = Precondition(
        lambda item: bool(item.store_path and _path_prefix_match(prefix, item.store_path))
    )
    matching_items = list(
        items_matching_precondition(ws, precondition & is_prefix_match, max_results=MAX_COMPLETIONS)
    )
    # Too many matches is not so useful.
    if len(matching_items) < MAX_COMPLETIONS:
        return {
            RichCompletion(
                fmt_store_path(item.store_path),
                display=f"{fmt_store_path(item.store_path)} ({precondition.name}) ",
                description=item.title or "",
                append_space=True,
            )
            for item in matching_items
            if item.store_path and _path_prefix_match(prefix, item.store_path)
        }


def completion_sort(completion: RichCompletion) -> Tuple[int, str]:
    return (len(completion.value), completion.value)


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def command_or_action_completer(context: CompletionContext) -> CompleterResult:
    """
    Completes command names. We don't complete on regular shell commands to keep it cleaner.
    """
    from kmd.xontrib.xonsh_customization import _actions, _commands

    if context.command and context.command.arg_index == 0:
        prefix = context.command.prefix

        command_matches = _completion_match(prefix, [c.__name__ for c in _commands.values()])
        command_completions = [
            RichCompletion(
                name,
                description=single_line(_commands[name].__doc__ or "xxx"),
                style=COLOR_COMMAND_TEXT,
            )
            for name in command_matches
        ]

        action_matches = _completion_match(prefix, [a.name for a in _actions.values()])
        action_completions = [
            RichCompletion(
                name,
                display=f"{name} {EMOJI_TASK}",
                description=single_line(_actions[name].description or "xxx"),
                style=COLOR_ACTION_TEXT,
                append_space=True,
            )
            for name in action_matches
        ]

        input_empty = not prefix.strip()
        help_completions = cast(
            List[RichCompletion], _completion_match(prefix, _all_help_completions(input_empty))
        )

        completions = sorted(
            command_completions + action_completions + help_completions, key=completion_sort
        )

        return set(completions)

    return None


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def item_completer(context: CompletionContext) -> CompleterResult:
    """
    If the current command is an action, complete with paths that match the precondition
    for that action.
    """
    from kmd.xontrib.xonsh_customization import _actions

    try:
        if context.command and context.command.arg_index >= 1:
            action_name = context.command.args[0].value
            action = _actions.get(action_name)
            prefix = context.command.prefix
            if action and action.precondition:
                return _item_completions(prefix, action.precondition)
    except InvalidState:
        return None
    return None


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def at_prefix_completer(context: CompletionContext) -> CompleterResult:
    """
    Completes items in the current workspace if prefixed with '@' sign.
    """
    try:
        if context.command and context.command.arg_index >= 1:
            prefix = context.command.prefix
            if prefix.startswith("@"):
                return _item_completions(prefix)
    except InvalidState:
        return None
    return None


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
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
            return set(_completion_match(query, _all_help_completions(False)))
    return None


def _param_completions(params: List[Param], prefix: str):
    return [
        RichCompletion(
            param.shell_prefix,
            description=param.description or "",
            append_space=(param.type == bool),
        )
        for param in params
        if param.shell_prefix.startswith(prefix)
    ]


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def options_completer(context: CompletionContext) -> CompleterResult:
    """
    Suggest options completions after a `-` or `--` on the command line.
    """
    from kmd.xontrib.xonsh_customization import _actions, _commands

    if context.command and context.command.arg_index > 0:
        prefix = context.command.prefix

        is_option = prefix.startswith("-")

        command_name = context.command.args[0].value

        command = _commands.get(command_name)
        action = _actions.get(command_name)

        if is_option:
            completions = []
            help_text = ""
            params: List[Param] = []

            if command:
                help_text = "Show more help for this command."
                params = annotate_param_info(command)
            elif action:
                help_text = "Show more help for this action."
                params = list(action.params)

            completions = _param_completions(params, prefix)

            if completions and "--help".startswith(prefix):
                completions.append(RichCompletion("--help", description=help_text))

            return set(completions) if completions else None


# FIXME: Complete enum values for enum options.


def add_key_bindings() -> None:

    custom_bindings = KeyBindings()

    @custom_bindings.add(" ")
    def _(event):
        """
        Map two spaces to `? ` to invoke an assistant question.
        """
        buf = event.app.current_buffer
        if buf.text == " ":
            buf.delete_before_cursor(2)
            buf.insert_text("? ")
        else:
            buf.insert_text(" ")

    @Condition
    def is_unquoted_assitant_request():
        app = get_app()
        buf = app.current_buffer
        text = buf.text.strip()
        return (
            buf.name == "DEFAULT_BUFFER"
            and text.startswith("?")
            and not (text.startswith('? "') or text.startswith("? '"))
        )

    @custom_bindings.add("enter", filter=is_unquoted_assitant_request)
    def _(event):
        """
        Automatically add quotes around assistant questions, so there are not
        syntax errors if the command line contains unclosed quotes etc.
        """

        buf = event.app.current_buffer
        text = buf.text.strip()

        # Wrap everything after '?' in quotes, preserving existing whitespace
        question_text = text[1:].strip()
        if not question_text:
            return None  # Don't let the user submit an empty question.

        buf.delete_before_cursor(len(buf.text))
        buf.insert_text(f"? {repr(question_text)}")

        buf.validate_and_handle()

    existing_bindings = __xonsh__.shell.shell.prompter.app.key_bindings  # type: ignore  # noqa: F821
    merged_bindings = merge_key_bindings([existing_bindings, custom_bindings])
    __xonsh__.shell.shell.prompter.app.key_bindings = merged_bindings  # type: ignore  # noqa: F821

    log.info("Added custom %s key bindings.", len(merged_bindings.bindings))


def load_completers():
    add_one_completer("command_or_action_completer", command_or_action_completer, "start")
    add_one_completer("item_completer", item_completer, "start")
    add_one_completer("at_prefix_completer", at_prefix_completer, "start")
    add_one_completer("help_question_completer", help_question_completer, "start")
    add_one_completer("options_completer", options_completer, "start")
