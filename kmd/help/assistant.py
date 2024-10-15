import json
from textwrap import dedent
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
from kmd.util.format_utils import fmt_path
from kmd.util.type_utils import not_none

log = get_logger(__name__)


@cached({})
def assistant_preamble(skip_api: bool = False, base_only: bool = False) -> str:
    from kmd.commands.command_defs import output_help_page  # Avoid circular imports.

    return dedent(
        f"""
        {fill_markdown(not_none(assistant_instructions.__doc__))} 


        {output_as_string(lambda: output_help_page(base_only))}


        {"" if skip_api else api_docs.__doc__} 
        """
    )


def _insert_output(func: Callable, name: str) -> str:
    try:
        return output_as_string(func)
    except (KmdRuntimeError, ValueError) as e:
        log.info("Skipping assistant input for %s: %s", name, e)
        return f"(No {name} available)"


def assistant_current_state() -> str:
    from kmd.commands.command_defs import (
        applicable_actions,
        history,
        select,
    )  # Avoid circular imports.

    path, is_sandbox = current_workspace_info()
    if path and not is_sandbox:
        current_state_message = Message(
            f"""
            CURRENT STATE

            Based on the current directory, the current workspace is: {path.name} at {fmt_path(path)}

            The last 5 commands issued by the user are:

            {_insert_output(history, "history")}

            The user's current selection is below:

            {_insert_output(select, "selection")}

            The actions with preconditions that match this selection, so are available to run on the
            current selection, are below:

            {_insert_output(applicable_actions, "applicable actions")}
            """
        )
    else:
        if is_sandbox:
            about_ws = "You are currently using the global sandbox workspace."
        else:
            about_ws = "The current directory is not a workspace."
        current_state_message = Message(
            f"""
            CURRENT STATE

            {about_ws}
            Create or switch to a workspace with the `workspace` command.
            For example:

            - `workspace my_new_workspace`.
            """
        )
    return current_state_message


def assistance(input: str, fast: bool = False) -> str:

    # TODO: Stream response.

    assistant_model = "assistant_model_fast" if fast else "assistant_model"

    model = not_none(get_param_value(assistant_model, type=LLM))

    output(f"Getting assistance (model {model})…")

    system_message = Message(
        f"""
        {assistant_preamble(skip_api=fast)}

        {assistant_current_state()}
        """
        # TODO: Include selection history, command history, any other info about the workspace.
    )

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

        print(assistant_response)

        return assistant_response.full_str()
    except (ValidationError, json.JSONDecodeError) as e:
        log.error("Error parsing assistant response: %s", e)
        raise e
