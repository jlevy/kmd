from textwrap import dedent
from kmd.action_exec.action_builders import define_llm_action
from kmd.config.logger import get_logger
from kmd.model.language_models import LLM
from kmd.text_docs.window_settings import WINDOW_4_PARA


log = get_logger(__name__)


define_llm_action(
    name="find_concepts",
    description="Identify the key concepts in a text.",
    model=LLM.gpt_4o.value,
    system_message=dedent(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    title_template="Concepts from {title}",
    template=dedent(
        """
        You are collecting concepts for the glossary of a book.
        
        - Identify and list names and key concepts from the following text.

        - Only include names of companies or people, other named entities, or specific or unusual or technical terms. Do not include common concepts or general ideas.

        - Each concept should be a single word or noun phrase.

        - Format your response as a list of bullet points in Markdown format.

        Input text:

        {body}

        Concepts:
        """
    ),
    windowing=WINDOW_4_PARA,
)