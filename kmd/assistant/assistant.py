from textwrap import dedent
from cachetools import cached
from kmd.action_exec.llm_completion import llm_completion
from kmd.config.settings import DEBUG_ASSISTANT
from kmd.text_formatting.markdown_normalization import wrap_markdown
from kmd.text_ui.command_output import fill_markdown, output_as_string
from kmd.docs import api_docs, assistant_instructions
from kmd.model.language_models import LLM


@cached({})
def assistant_preamble(fast: bool = False):
    from kmd.commands.commands import kmd_help  # Avoid circular imports.

    if fast:
        return f"""
        {fill_markdown(assistant_instructions.__doc__)}


        {output_as_string(kmd_help)}
        """
    else:

        return dedent(
            f"""
            {fill_markdown(assistant_instructions.__doc__)}


            {output_as_string(kmd_help)}


            {api_docs.__doc__} 
            """
        )


def assistance(input: str, fast: bool = False) -> str:

    from kmd.commands.commands import select  # Avoid circular imports.

    model = LLM.groq_llama3_70b_8192 if fast else LLM.gpt_4o

    system_message = dedent(
        f"""
        {assistant_preamble(fast=fast)}

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
            model.value,
            system_message=system_message,
            template=template,
            input=input,
            save_objects=DEBUG_ASSISTANT,
        )
    )
