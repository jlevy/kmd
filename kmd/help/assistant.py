import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

from cachetools import cached
from pydantic import ValidationError

from kmd.config.logger import get_logger
from kmd.config.settings import global_settings
from kmd.docs import api_docs, assistant_instructions
from kmd.errors import InvalidState, KmdRuntimeError
from kmd.file_formats.chat_format import (
    append_chat_message,
    ChatHistory,
    ChatMessage,
    ChatRole,
    tail_chat_history,
)
from kmd.lang_tools.capitalization import capitalize_cms
from kmd.llms.llm_completion import llm_completion
from kmd.model.args_model import fmt_loc
from kmd.model.assistant_response_model import AssistantResponse
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType
from kmd.model.language_models import LLM
from kmd.model.messages_model import Message
from kmd.model.script_model import Script
from kmd.shell.assistant_output import print_assistant_response
from kmd.shell.shell_output import cprint, output_as_string
from kmd.text_formatting.markdown_normalization import normalize_markdown
from kmd.util.format_utils import fmt_paras
from kmd.util.log_calls import log_calls
from kmd.util.parse_shell_args import shell_unquote
from kmd.util.type_utils import not_none
from kmd.workspaces.workspaces import current_workspace, workspace_param_value


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
    except (KmdRuntimeError, ValueError, FileNotFoundError) as e:
        log.info("Skipping assistant input for %s: %s", name, e)
        output = f"(No {name} available)"

    log.info("Including %s lines of output to assistant for %s", output.count("\n"), name)

    return f"(output from command`{name}`:)\n\n{output}"


@log_calls(level="warning", if_slower_than=0.5)
def assist_current_state() -> Message:
    from kmd.commands.command_defs import (
        applicable_actions,
        files,
        history,
        select,
    )  # Avoid circular imports.

    ws = current_workspace()
    ws_base_dir = ws.base_dir
    is_sandbox = ws.is_sandbox

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


@log_calls(level="info")
def assist_system_message_with_state(skip_api: bool = False) -> Message:
    return Message(
        f"""
        {assist_preamble(skip_api=skip_api)}

        {assist_current_state()}
        """
        # TODO: Include selection history, command history, any other info about files in the workspace.
    )


def assistant_history_file() -> Path:
    ws = current_workspace()
    return ws.base_dir / ws.dirs.assistant_history_yml


def assistant_chat_history(include_system_message: bool, fast: bool = False) -> ChatHistory:
    assistant_history = ChatHistory()
    try:
        assistant_history = tail_chat_history(assistant_history_file(), max_records=20)
    except FileNotFoundError:
        log.info("No assistant history file found: %s", assistant_history_file)
    except (InvalidState, ValueError) as e:
        log.warning("Couldn't load assistant history, so skipping it: %s", e)

    if include_system_message:
        system_message = assist_system_message_with_state(skip_api=fast)
        assistant_history.messages.insert(0, ChatMessage(ChatRole.system, system_message))

    return assistant_history


def general_assistance(
    model: LLM,
    messages: List[Dict[str, str]],
) -> AssistantResponse:
    # TODO: Stream response.

    # Get the assistant's response, including history.
    response = llm_completion(
        model,
        messages=messages,
        save_objects=global_settings().debug_assistant,
        response_format=AssistantResponse,
    )

    try:
        response_data = json.loads(response.content)
        assistant_response = AssistantResponse.model_validate(response_data)
        log.debug("Assistant response: %s", assistant_response)
    except (ValidationError, json.JSONDecodeError) as e:
        log.error("Error parsing assistant response: %s", e)
        raise e

    return assistant_response


def shell_context_assistance(
    input: str, fast: bool = False, silent: bool = False, model: Optional[LLM] = None
) -> None:

    if not model:
        assistant_model = "assistant_model_fast" if fast else "assistant_model"
        model = not_none(workspace_param_value(assistant_model, type=LLM))

    if not silent:
        cprint(f"Getting assistance (model {model})…")

    # Get shell chat history.
    history_file = assistant_history_file()
    history = assistant_chat_history(include_system_message=False, fast=fast)

    # Insert the system message.
    system_message = assist_system_message_with_state(skip_api=fast)
    history.messages.insert(0, ChatMessage(ChatRole.system, system_message))

    # Record the user's message.
    input = shell_unquote(input)
    log.info("User request to assistant: %s", input)
    user_message = ChatMessage(ChatRole.user, input)
    history.append(user_message)
    log.info("Assistant history context (including new message): %s", history.size_summary())

    # Get the assistant's response.
    assistant_response = general_assistance(model, history.as_chat_completion())

    # Save the user message to the history after a response. That way if the
    # use changes their mind right away and cancels it's not left in the file.
    append_chat_message(history_file, user_message)
    # Record the assistant's response, in structured format.
    append_chat_message(
        history_file, ChatMessage(ChatRole.assistant, assistant_response.model_dump())
    )

    print_assistant_response(assistant_response, model)

    if assistant_response.suggested_commands:
        response_text = normalize_markdown(assistant_response.response_text)

        script = Script(
            commands=assistant_response.suggested_commands,
            description=None,  # Let's put the response text in the item description instead.
            signature=None,  # TODO Infer from first command.
        )
        item = Item(
            type=ItemType.script,
            title=f"Assistant Answer: {capitalize_cms(input)}",
            description=response_text,
            format=Format.kmd_script,
            body=script.script_str(),
        )
        ws = current_workspace()
        ws.save(item, as_tmp=True)
