from textwrap import dedent
from cachetools import cached
from kmd.action_exec.llm_completion import llm_completion
from kmd.config.settings import DEBUG_ASSISTANT
from kmd.file_storage.workspaces import current_workspace
from kmd.text_formatting.markdown_normalization import wrap_markdown
from kmd.text_ui.command_output import fill_markdown, output, output_as_string
from kmd.docs import api_docs, assistant_instructions
from kmd.util.type_utils import not_none


@cached({})
def assistant_preamble(skip_api: bool = False, base_only: bool = False) -> str:
    from kmd.commands.commands import output_help  # Avoid circular imports.

    return dedent(
        f"""
        {fill_markdown(assistant_instructions.__doc__)}


        {output_as_string(lambda: output_help(base_only))}


        {"" if skip_api else api_docs.__doc__} 
        """
    )


def assistance(input: str, fast: bool = False) -> str:
    from kmd.commands.commands import select  # Avoid circular imports.

    assistant_model = "assistant_model_fast" if fast else "assistant_model"
    model_str = not_none(current_workspace().get_action_param(assistant_model))

    output(f"Getting assistance (model {model_str})…")

    system_message = dedent(
        f"""
        {assistant_preamble(skip_api=fast)}

        CURRENT USER STATE

        The user's current selection is below:

        {output_as_string(select)}
        """
        # TODO: Include selection history, command history, and other info about the workspace.
    )

    template = dedent(
        """
        Here is the user's request:
        
        {body}

        Give your response:
        """
    )

    # TODO: Stream response.
    return wrap_markdown(
        llm_completion(
            model_str,
            system_message=system_message,
            template=template,
            input=input,
            save_objects=DEBUG_ASSISTANT,
        )
    )
