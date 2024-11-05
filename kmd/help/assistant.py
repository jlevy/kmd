import json
from typing import Callable

from cachetools import cached
from pydantic import ValidationError
from rich.text import Text

from kmd.config.logger import get_logger
from kmd.config.settings import global_settings
from kmd.config.text_styles import COLOR_HEADING, COLOR_HINT, COLOR_STATUS, EMOJI_ASSISTANT
from kmd.docs import api_docs, assistant_instructions
from kmd.errors import InvalidState, KmdRuntimeError
from kmd.file_formats.chat_format import (
    append_chat_message,
    ChatHistory,
    ChatMessage,
    ChatRole,
    tail_chat_history,
)
from kmd.llms.llm_completion import llm_template_completion
from kmd.model.args_model import fmt_loc
from kmd.model.assistant_response_model import AssistantResponse, Confidence
from kmd.model.language_models import LLM
from kmd.model.messages_model import Message
from kmd.shell.shell_output import (
    cprint,
    output_as_string,
    print_assistance,
    print_code_block,
    print_small_heading,
    print_style,
    print_text_block,
    Style,
    Wrap,
)
from kmd.text_formatting.markdown_normalization import fill_markdown
from kmd.util.format_utils import fmt_paras
from kmd.util.parse_shell_args import shell_unquote
from kmd.util.type_utils import not_none
from kmd.workspaces.workspaces import current_workspace, current_workspace_info, get_param_value


log = get_logger(__name__)


@cached({})
def assist_preamble(skip_api: bool = False, base_actions_only: bool = False) -> str:
    from kmd.help.help_page import print_manual  # Avoid circular imports.

    return fmt_paras(
        str(assistant_instructions),
        output_as_string(lambda: print_manual(base_actions_only)),
        None if skip_api else api_docs,
    )


def _insert_output(func: Callable, name: str) -> str:
    try:
        output = output_as_string(func)
    except (KmdRuntimeError, ValueError) as e:
        log.info("Skipping assistant input for %s: %s", name, e)
        output = f"(No {name} available)"

    log.info("Including %s lines of output to assistant for %s", output.count("\n"), name)

    return f"(output from command`{name}`:)\n\n{output}"


def assist_current_state() -> Message:
    from kmd.commands.command_defs import (
        applicable_actions,
        files,
        history,
        select,
    )  # Avoid circular imports.

    ws_dirs, is_sandbox = current_workspace_info()
    ws_base_dir = ws_dirs.base_dir if ws_dirs else None

    if ws_base_dir and not is_sandbox:
        ws_info = f"Based on the current directory, the current workspace is: {ws_base_dir.name} at {fmt_loc(ws_base_dir)}"
    else:
        if is_sandbox:
            about_ws = "You are currently using the global sandbox workspace."
        else:
            about_ws = "The current directory is not a workspace."
        ws_info = (
            f"{about_ws}. Create or switch to a workspace with the `workspace` command."
            "For example: `workspace my_new_workspace`."
        )

    log.info("Assistant current workspace state: %s", ws_info)

    # FIXME: Add @-mentioned files into context.

    current_state_message = Message(
        f"""
        ## Current State

        {ws_info}

        The last few commands issued by the user are:

        {_insert_output(lambda: history(max=30), "history")}

        The user's current selection is below:

        {_insert_output(select, "selection")}

        The actions with preconditions that match this selection, so are available to run on the
        current selection, are below:

        {_insert_output(applicable_actions, "applicable_actions")}

        And here is an overview of the files in the current directory:

        {_insert_output(lambda: files(brief=True), "files --brief")}
        """
    )

    return current_state_message


def assist_system_message(skip_api: bool = False) -> Message:
    return Message(
        f"""
        {assist_preamble(skip_api=skip_api)}

        {assist_current_state()}
        """
        # TODO: Include selection history, command history, any other info about files in the workspace.
    )


def print_assistant_response(response: AssistantResponse, model: LLM) -> None:
    with print_style(Style.PAD):
        assistant_name = Text(f"{EMOJI_ASSISTANT} Kmd Assistant", style=COLOR_HEADING)
        info = Text(f"({model}) [{response.confidence.value}]", style=COLOR_HINT)
        cprint(assistant_name + " " + info)
        cprint()

        if response.response_text:
            if response.confidence in {Confidence.direct_answer, Confidence.partial_answer}:
                print_text_block(fill_markdown(response.response_text))
            else:
                print_assistance(fill_markdown(response.response_text))

        if response.suggested_commands:
            formatted_commands = "\n\n".join(c.full_str() for c in response.suggested_commands)
            print_small_heading("Suggested commands:")
            print_code_block(formatted_commands)

        if response.see_also:
            formatted_see_also = ", ".join(f"`{cmd}`" for cmd in response.see_also)
            print_small_heading("See also:")
            cprint(formatted_see_also, color=COLOR_STATUS, text_wrap=Wrap.WRAP_INDENT)


def assistance(input: str, fast: bool = False) -> None:
    # TODO: Stream response.

    assistant_model = "assistant_model_fast" if fast else "assistant_model"
    model = not_none(get_param_value(assistant_model, type=LLM))

    cprint(f"Getting assistance (model {model})…")

    system_message = assist_system_message(skip_api=fast)

    assistant_history = ChatHistory()
    try:
        ws = current_workspace()
        assistant_history_file = ws.base_dir / ws.dirs.assistant_history_yml
        assistant_history = tail_chat_history(assistant_history_file, max_records=20)
    except FileNotFoundError:
        log.info("No assistant history file found: %s", assistant_history_file)
    except (InvalidState, ValueError) as e:
        log.warning("Couldn't load assistant history, so skipping it: %s", e)

    # Get and record the user's message.
    input = shell_unquote(input)
    log.info("User request to assistant: %s", input)
    append_chat_message(assistant_history_file, ChatMessage(ChatRole.user, input))

    # Get the assistant's response, including history.
    response = llm_template_completion(
        model,
        system_message=system_message,
        input=input,
        previous_messages=assistant_history.as_chat_completion(),
        save_objects=global_settings().debug_assistant,
        response_format=AssistantResponse,
    )

    try:
        response_data = json.loads(response.content)
        assistant_response = AssistantResponse.model_validate(response_data)
        log.debug("Assistant response: %s", assistant_response)

        # Record the assistant's response, in structured format.
        append_chat_message(
            assistant_history_file, ChatMessage(ChatRole.assistant, assistant_response.model_dump())
        )

        print_assistant_response(assistant_response, model)

    except (ValidationError, json.JSONDecodeError) as e:
        log.error("Error parsing assistant response: %s", e)
        raise e
