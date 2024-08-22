from kmd.model.actions_model import LLMMessage, LLMTemplate, TitleTemplate
from kmd.exec.action_registry import kmd_action
from kmd.model.llm_actions_model import CachedLLMAction
from kmd.text_docs.window_settings import WINDOW_4_PARA
from kmd.config.logger import get_logger

log = get_logger(__name__)


@kmd_action()
class FindConcepts(CachedLLMAction):
    def __init__(self):
        super().__init__(
            name="find_concepts",
            description="Identify the key concepts in a text. Processes each div chunk.",
            system_message=LLMMessage(
                """
                You are a careful and precise editor.
                You give exactly the results requested without additional commentary.
                """
            ),
            title_template=TitleTemplate("Concepts from {title}"),
            template=LLMTemplate(
                """
                You are collecting concepts for the glossary of a book.
                
                - Identify and list names and key concepts from the following text.

                - Only include names of companies or people, other named entities, or specific or
                  unusual or technical terms. Do not include common concepts or general ideas.

                - Each concept should be a single word or noun phrase.

                - Do NOT include numerical quantities like "40% more gains" or "3 people".

                - Do NOT include meta-information about the document such as "description", "link",
                  "summary", "research paper", or any other language describing the document itself.

                - Format your response as a list of bullet points in Markdown format.

                - If the input is very short or so unclear you can't perform this task, simply output
                  "(No results)".

                Input text:

                {body}

                Concepts:
                """
            ),
            windowing=WINDOW_4_PARA,
        )
