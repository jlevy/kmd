from textwrap import dedent
from kmd.action_exec.action_builders import define_llm_action
from kmd.model.language_models import LLM

define_llm_action(
    name="describe_briefly",
    description="Very brief description of text, in at most three sentences.",
    model=LLM.gpt_4o.value,
    system_message=dedent(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    title_template="Summary of {title}",
    template=dedent(
        """
        Give a brief description of the entire text below, as a summary of two or three sentences.
        Write it concisely and clearly, in a form suitable for a short description of a web page
        or article.

        Original text:

        {body}

        Brief description of the text:
        """
    ),
)