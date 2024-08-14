from textwrap import dedent
from cachetools import cached
from kmd.llms.llm_completion import llm_completion
from kmd.config.settings import get_settings
from kmd.file_storage.workspaces import current_workspace_name, get_param_value
from kmd.model.actions_model import LLMMessage, LLMTemplate
from kmd.model.language_models import LLM
from kmd.text_formatting.markdown_normalization import wrap_markdown
from kmd.text_ui.command_output import fill_markdown, output, output_as_string
from kmd.docs import api_docs, assistant_instructions
from kmd.util.type_utils import not_none


@cached({})
def assistant_preamble(skip_api: bool = False, base_only: bool = False) -> str:
    from kmd.commands.commands import output_help_page  # Avoid circular imports.

    return dedent(
        f"""
        {fill_markdown(assistant_instructions.__doc__)}


        {output_as_string(lambda: output_help_page(base_only))}


        {"" if skip_api else api_docs.__doc__} 
        """
    )


def assistance(input: str, fast: bool = False) -> str:
    from kmd.commands.commands import select, applicable_actions  # Avoid circular imports.

    assistant_model = "assistant_model_fast" if fast else "assistant_model"

    model = LLM(not_none(get_param_value(assistant_model)))

    output(f"Getting assistance (model {model})…")

    ws_name = current_workspace_name()
    if ws_name:
        current_state_message = LLMMessage(
            f"""
            CURRENT STATE

            Current workspace is: {ws_name}

            The user's current selection is below:

            {output_as_string(select)}

            The actions with preconditions that match this selection, so are available to run on the
            current selection, are below:

            {output_as_string(applicable_actions)}
            """
        )
    else:
        current_state_message = LLMMessage(
            """
            CURRENT STATE

            The current directory is not a workspace. Create or switch to a workspace with the `workspace` command.
            For example:

            - `workspace my_new_workspace`.
            """
        )

    system_message = LLMMessage(
        f"""
        {assistant_preamble(skip_api=fast)}

        {current_state_message}

        """
        # TODO: Include selection history, command history, any other info about the workspace.
    )

    template = LLMTemplate(
        """
        Here is the user's request:
        
        {body}

        Give your response:
        """
    )

    # TODO: Stream response.
    return wrap_markdown(
        llm_completion(
            model,
            system_message=system_message,
            template=template,
            input=input,
            save_objects=get_settings().debug_assistant,
        )
    )
