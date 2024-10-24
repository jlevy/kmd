import json
from typing import Callable

from cachetools import cached
from pydantic import ValidationError

from kmd.config.logger import get_logger
from kmd.config.settings import global_settings
from kmd.docs import api_docs, assistant_instructions
from kmd.errors import KmdRuntimeError
from kmd.file_storage.workspaces import current_workspace_info, get_param_value
from kmd.llms.llm_completion import llm_template_completion
from kmd.model.assistant_model import AssistantResponse
from kmd.model.language_models import LLM
from kmd.model.messages_model import Message, MessageTemplate
from kmd.text_ui.command_output import fill_markdown, output, output_as_string
from kmd.util.format_utils import fmt_paras, fmt_path
from kmd.util.type_utils import not_none

log = get_logger(__name__)


@cached({})
def assist_preamble(skip_api: bool = False, base_actions_only: bool = False) -> str:
    from kmd.help.help_page import output_help_page  # Avoid circular imports.

    return fmt_paras(
        fill_markdown(str(assistant_instructions)),
        output_as_string(lambda: output_help_page(base_actions_only)),
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
        ws_info = f"Based on the current directory, the current workspace is: {ws_base_dir.name} at {fmt_path(ws_base_dir)}"
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

    current_state_message = Message(
        f"""
        CURRENT STATE

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


def assistance(input: str, fast: bool = False) -> str:

    # TODO: Stream response.

    assistant_model = "assistant_model_fast" if fast else "assistant_model"

    model = not_none(get_param_value(assistant_model, type=LLM))

    output(f"Getting assistance (model {model})…")

    system_message = assist_system_message(skip_api=fast)

    template = MessageTemplate(
        """
        Here is the user's request:
        
        {body}

        Give your response:
        """
    )

    response = llm_template_completion(
        model,
        system_message=system_message,
        template=template,
        input=input,
        save_objects=global_settings().debug_assistant,
        response_format=AssistantResponse,
    )

    try:
        response_data = json.loads(response.content)
        assistant_response = AssistantResponse.model_validate(response_data)

        return assistant_response.full_str()
    except (ValidationError, json.JSONDecodeError) as e:
        log.error("Error parsing assistant response: %s", e)
        raise e
