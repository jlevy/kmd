from textwrap import dedent
from kmd.action_exec.llm_completion import llm_completion
from kmd.text_ui.command_output import output_as_string
from kmd.docs import assistant_instructions
from kmd import model_sources_str
from kmd.model.language_models import LLM


def assistance(input: str) -> str:
    from kmd.commands.commands import kmd_help, select  # Avoid circular imports.

    model = LLM.gpt_4o.value

    system_message = dedent(
        f"""
        {assistant_instructions.__doc__}

        Here is the kmd help page:

        {output_as_string(kmd_help)}

        Here is the kmd source code representing the data model of Python classes for items
        and actions:

        {model_sources_str}

        The user's current seletion is below:

        {output_as_string(select)}
        """
    )

    template = dedent(
        """
        Here is the user's request:
        
        {body}

        Give your response:
        """
    )

    # TODO: Stream response.
    return llm_completion(
        model,
        system_message=system_message,
        template=template,
        input=input,
        save_objects=False,
    )
