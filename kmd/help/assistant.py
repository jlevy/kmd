import json
from enum import Enum
from functools import cache
from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import ValidationError

from kmd.config.logger import get_logger, record_console
from kmd.config.settings import global_settings
from kmd.config.text_styles import EMOJI_WARN
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
from kmd.llms.llm_completion import llm_completion, LLMCompletionResult
from kmd.model.args_model import fmt_loc
from kmd.model.assistant_response_model import AssistantResponse
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType
from kmd.model.language_models import LLM
from kmd.model.messages_model import Message
from kmd.model.script_model import Script
from kmd.shell_ui.assistant_output import print_assistant_response
from kmd.shell_ui.rich_markdown_kyrm import KyrmMarkdown
from kmd.shell_ui.shell_output import cprint, print_assistance
from kmd.text_wrap.markdown_normalization import normalize_markdown
from kmd.util.log_calls import log_calls
from kmd.util.parse_shell_args import shell_unquote
from kmd.util.type_utils import not_none
from kmd.workspaces.workspaces import current_workspace, workspace_param_value


log = get_logger(__name__)


class AssistanceType(Enum):
    """
    Types of assistance offered, based on the model.
    """

    careful = "careful"
    structured = "structured"
    basic = "basic"
    fast = "fast"

    @property
    def param_name(self) -> str:
        if self == AssistanceType.careful:
            return "default_careful_llm"
        elif self == AssistanceType.structured:
            return "default_structured_llm"
        elif self == AssistanceType.basic:
            return "default_basic_llm"
        elif self == AssistanceType.fast:
            return "default_fast_llm"
        else:
            raise ValueError(f"Invalid assistance type: {self}")

    @property
    def default_model(self) -> LLM:
        return not_none(workspace_param_value(self.param_name, type=LLM))

    @property
    def is_structured(self) -> bool:
        return self == AssistanceType.structured

    @property
    def skip_api_docs(self) -> bool:
        return self == AssistanceType.fast


@cache
def assist_preamble(
    is_structured: bool, skip_api_docs: bool = False, base_actions_only: bool = False
) -> str:
    from kmd.help.help_page import print_manual  # Avoid circular imports.

    with record_console() as console:
        cprint(str(assistant_instructions(is_structured)))
        print_manual(base_actions_only)
        if not skip_api_docs:
            cprint(api_docs)

    preamble = console.export_text()
    log.info("Assistant preamble: %s chars (%s lines)", len(preamble), preamble.count("\n"))
    return preamble


def _insert_output(func: Callable, name: str) -> str:
    with record_console() as console:
        try:
            func()
        except (KmdRuntimeError, ValueError, FileNotFoundError) as e:
            log.info("Skipping assistant input for %s: %s", name, e)
            output = f"(No {name} available)"

    output = console.export_text()
    log.info("Including %s lines of output to assistant for %s", output.count("\n"), name)

    return f"(output from command`{name}`:)\n\n{output}"


@log_calls(level="warning", if_slower_than=0.5)
def assist_current_state() -> Message:
    from kmd.commands.workspace_commands import (
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
    log.info(
        "Assistant current state message: %s chars (%s lines)",
        len(current_state_message),
        current_state_message.count("\n"),
    )
    return current_state_message


@log_calls(level="info")
def assist_system_message_with_state(is_structured: bool, skip_api_docs: bool = False) -> Message:
    return Message(
        f"""
        {assist_preamble(is_structured=is_structured, skip_api_docs=skip_api_docs)}

        {assist_current_state()}
        """
        # TODO: Include selection history, command history, any other info about files in the workspace.
    )


def assistant_history_file() -> Path:
    ws = current_workspace()
    return ws.base_dir / ws.dirs.assistant_history_yml


def assistant_chat_history(
    include_system_message: bool, is_structured: bool, skip_api_docs: bool = False
) -> ChatHistory:
    assistant_history = ChatHistory()
    try:
        assistant_history = tail_chat_history(assistant_history_file(), max_records=20)
    except FileNotFoundError:
        log.info("No assistant history file found: %s", assistant_history_file)
    except (InvalidState, ValueError) as e:
        log.warning("Couldn't load assistant history, so skipping it: %s", e)

    if include_system_message:
        system_message = assist_system_message_with_state(
            is_structured=is_structured, skip_api_docs=skip_api_docs
        )
        assistant_history.messages.insert(0, ChatMessage(ChatRole.system, system_message))

    return assistant_history


def assistance_unstructured(messages: List[Dict[str, str]], model: LLM) -> LLMCompletionResult:
    """
    Get general assistance, with unstructured output.
    Must provide all context within the messages.
    """
    # TODO: Stream response.

    return llm_completion(
        model,
        messages=messages,
        save_objects=global_settings().debug_assistant,
    )


def assistance_structured(messages: List[Dict[str, str]], model: LLM) -> AssistantResponse:
    """
    Get general assistance, with unstructured or structured output.
    Must provide all context within the messages.
    """

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
    input: str,
    silent: bool = False,
    model: Optional[LLM] = None,
    assistance_type: AssistanceType = AssistanceType.basic,
) -> None:
    """
    Get assistance, using the full context of the shell.
    """

    if not model:
        model = assistance_type.default_model

    if not silent:
        cprint(f"Getting assistance ({assistance_type.name}, model {model})…")

    # Get shell chat history.
    skip_api_docs = assistance_type.skip_api_docs
    is_structured = assistance_type.is_structured
    history = assistant_chat_history(
        include_system_message=False, is_structured=is_structured, skip_api_docs=skip_api_docs
    )

    # Insert the system message.
    system_message = assist_system_message_with_state(
        is_structured=is_structured, skip_api_docs=skip_api_docs
    )
    history.messages.insert(0, ChatMessage(ChatRole.system, system_message))

    # Record the user's message.
    input = shell_unquote(input)
    log.info("User request to assistant: %s", input)
    user_message = ChatMessage(ChatRole.user, input)
    history.append(user_message)
    log.info("Assistant history context (including new message): %s", history.size_summary())

    # Get the assistant's response.
    if assistance_type.is_structured:
        assistant_response = assistance_structured(history.as_chat_completion(), model)

        # Save the user message to the history after a response. That way if the
        # use changes their mind right away and cancels it's not left in the file.
        history_file = assistant_history_file()
        append_chat_message(history_file, user_message)
        # Record the assistant's response, in structured format.
        append_chat_message(
            history_file, ChatMessage(ChatRole.assistant, assistant_response.model_dump())
        )

        print_assistant_response(assistant_response, model)

        # If the assistant suggests commands, also save them as a script.
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

    else:
        assistant_response = assistance_unstructured(history.as_chat_completion(), model)
        print_assistance(KyrmMarkdown(assistant_response.content))

    # FIXME: Make these obvious buttons.
    if assistance_type in (AssistanceType.fast, AssistanceType.basic):
        cprint()
        print_assistance(
            f"{EMOJI_WARN} For more detailed assistance, use `assist --type=careful` or `assist --type=structured`."
        )
