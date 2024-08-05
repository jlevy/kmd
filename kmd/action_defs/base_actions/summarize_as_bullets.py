from textwrap import dedent
from kmd.action_exec.action_builders import define_llm_action
from kmd.model.language_models import LLM
from kmd.text_docs.window_settings import WINDOW_4_PARA


define_llm_action(
    name="summarize_as_bullets",
    description="Summarize text as bullet points.",
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
        Summarize the following text as a list of concise bullet points:

        - Each point should be one sentence long.
        
        - Include all key numbers or facts, without omitting any claims or important details.
        
        - Use simple and precise language.

        - It is very important you do not add any details that are not directly stated in the original text. Do not change any numbers or alter its meaning in any way.

        - Format your response as a list of bullet points in Markdown format.

        Input text:

        {body}

        Bullet points:
        """
    ),
    windowing=WINDOW_4_PARA,
)
