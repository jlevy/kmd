from typing import Iterable, List, Tuple

from xonsh.completers.completer import RichCompletion
from xonsh.completers.tools import CompleterResult, CompletionContext, contextual_completer

from kmd.config.text_styles import COLOR_ACTION_TEXT, COLOR_COMMAND_TEXT, EMOJI_TASK
from kmd.docs.faq_headings import faq_headings
from kmd.errors import InvalidState
from kmd.file_storage.workspaces import current_workspace
from kmd.help.function_param_info import annotate_param_info
from kmd.model.params_model import Param
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_checks import items_matching_precondition
from kmd.util.format_utils import fmt_path, single_line
from kmd.xontrib.xonsh_customization import _actions, _commands

MAX_COMPLETIONS = 500


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
                            fmt_path(item.store_path),
                            display=f"{fmt_path(item.store_path)} ({action.precondition.name}) ",
                            description=item.title or "",
                            append_space=True,
                        )
                        for item in matching_items
                        if item.store_path and item.store_path.startswith(prefix)
                    }
    except InvalidState:
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
            questions = faq_headings()

            return {RichCompletion(question) for question in _completion_match(query, questions)}


def _param_completions(params: List[Param], prefix: str):
    return [
        RichCompletion(
            param.shell_prefix(),
            description=param.description or "",
            append_space=(param.type == bool),
        )
        for param in params
        if param.shell_prefix().startswith(prefix)
    ]


@contextual_completer
def options_completer(context: CompletionContext) -> CompleterResult:
    """
    Suggest options completions after a `-` or `--` on the command line.
    """
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


# TODO: Complete enum values for enum options.
