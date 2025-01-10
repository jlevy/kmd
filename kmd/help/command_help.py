from typing import List, Optional

from kmd.action_defs import look_up_action
from kmd.commands.command_registry import CommandFunction, look_up_command
from kmd.errors import InvalidInput, NoMatch
from kmd.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole
from kmd.help.assistant import assist_preamble, assistance_unstructured
from kmd.help.docstrings import parse_docstring
from kmd.help.function_param_info import annotate_param_info
from kmd.help.tldr_help import tldr_help
from kmd.model.actions_model import Action
from kmd.model.language_models import LLM
from kmd.model.messages_model import Message
from kmd.model.params_model import Param, RUNTIME_ACTION_PARAMS
from kmd.model.preconditions_model import Precondition

from kmd.shell_ui.rich_markdown_custom import Markdown
from kmd.shell_ui.shell_output import (
    cprint,
    format_name_and_description,
    print_assistance,
    print_help,
)
from kmd.text_wrap.text_styling import DEFAULT_INDENT, Wrap


GENERAL_HELP = (
    "For more information, ask the assistant a question "
    "(press space twice or type `?`) or check `help`."
)


def _print_command_help(
    name: str,
    description: Optional[str] = None,
    param_info: Optional[List[Param]] = None,
    precondition: Optional[Precondition] = None,
    verbose: bool = True,
    is_action: bool = False,
):
    command_str = f"the `{name}` command" if name else "this command"

    cprint()

    if not description:
        print_help(f"Sorry, no help available for {command_str}.")
    else:
        docstring = parse_docstring(description)

        cprint(format_name_and_description(name, docstring.body))

        if precondition:
            cprint()
            cprint(
                "Precondition: " + str(precondition),
                text_wrap=Wrap.HANGING_INDENT,
                extra_indent=DEFAULT_INDENT,
            )

        if param_info:
            cprint()
            cprint("Options:", extra_indent=DEFAULT_INDENT)
            cprint()
            for param in param_info:

                if param.type == bool:
                    param_doc = f"--{param.name}"
                else:
                    param_doc = f"--{param.name}=<value>"

                if param.name in docstring.param:
                    param_desc = docstring.param[param.name]
                elif param.description:
                    param_desc = param.full_description
                else:
                    param_desc = ""

                if param_desc:
                    param_doc += f": {param_desc}"

                cprint(
                    param_doc,
                    text_wrap=Wrap.HANGING_INDENT,
                    extra_indent=DEFAULT_INDENT,
                )
                cprint()

    if verbose:
        cprint()
        if is_action:
            source_hint = (
                f" Use `action_source_code {name}` to see the source code for this action."
            )
        else:
            source_hint = ""
        print_help(GENERAL_HELP + source_hint)
        cprint()


def print_command_function_help(command: CommandFunction, verbose: bool = True):
    param_info = annotate_param_info(command)

    _print_command_help(
        command.__name__,
        command.__doc__ if command.__doc__ else "",
        param_info=param_info,
        verbose=verbose,
        is_action=False,
    )


def print_action_help(action: Action, verbose: bool = True):
    params: List[Param] = []
    if verbose:
        params = list(action.params) + list(RUNTIME_ACTION_PARAMS.values())

    _print_command_help(
        action.name,
        action.description,
        param_info=params,
        precondition=action.precondition,
        verbose=verbose,
        is_action=True,
    )


def explain_command(text: str, assistant_model: Optional[LLM] = None):
    """
    Explain a command or action or give a brief explanation of something.
    Checks tldr and help docs first. If `assistant_model` is provided and docs
    are not available, use the assistant.
    """
    text = text.strip()

    tldr_help_str = tldr_help(text)
    if tldr_help_str:
        print_assistance(Markdown(tldr_help_str))
        return

    help_str = None
    try:
        command = look_up_command(text)
        print_command_function_help(command)
        return
    except InvalidInput:
        pass

    if not help_str:
        try:
            action = look_up_action(text)
            print_action_help(action)
            return
        except InvalidInput:
            pass

    if not help_str and assistant_model:
        chat_history = ChatHistory()

        # Give the LLM full context on kmd APIs.
        # But we do this here lazily to prevent circular dependencies.
        system_message = Message(assist_preamble(skip_api_docs=False, base_actions_only=False))
        chat_history.extend(
            [
                ChatMessage(ChatRole.system, system_message),
                ChatMessage(ChatRole.user, f"Can you explain this succinctly: {text}"),
            ]
        )

        response = assistance_unstructured(chat_history.as_chat_completion(), model=assistant_model)
        help_str = response.content

    if help_str:
        print_assistance(help_str)
    else:
        raise NoMatch(f"Sorry, no help found for `{text}`")
