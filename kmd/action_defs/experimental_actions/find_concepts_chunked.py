from kmd.config.settings import DEFAULT_CAREFUL_MODEL
from kmd.exec.llm_transforms import llm_transform_str
from kmd.model.actions_model import LLMMessage, LLMTemplate, TitleTemplate
from kmd.exec.action_registry import kmd_action
from kmd.model.html_conventions import CONCEPTS
from kmd.model.llm_actions_model import ChunkedLLMAction
from kmd.text_chunks.parse_divs import TextNode
from kmd.text_chunks.chunk_divs import div, get_original, insert_chunk_child
from kmd.text_docs.window_settings import WINDOW_4_PARA
from kmd.config.logger import get_logger

log = get_logger(__name__)


@kmd_action
class FindConceptsChunked(ChunkedLLMAction):
    def __init__(self):
        super().__init__(
            name="find_concepts_chunked",  # Updated name
            description="Identify the key concepts in a text. Processes each div chunk.",
            model=DEFAULT_CAREFUL_MODEL,
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

    def process_chunk(self, chunk: TextNode) -> str:
        transform_input = get_original(chunk)

        llm_response = llm_transform_str(self, transform_input)

        new_div = div(CONCEPTS, llm_response)

        return insert_chunk_child(chunk, new_div)
