from kmd.concepts.concept_formats import concepts_from_markdown
from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.exec.llm_transforms import llm_transform_item
from kmd.model import Item, LLMAction, Message, MessageTemplate, TitleTemplate
from kmd.text_docs.window_settings import WINDOW_64_PARA, WindowSettings
from kmd.text_formatting.markdown_util import as_bullet_points
from kmd.util.type_utils import not_none

log = get_logger(__name__)


@kmd_action
class FindConcepts(LLMAction):

    name: str = "find_concepts"

    description: str = """
        Identify the key concepts in a text. Processes each div chunk.
        """

    system_message: Message = Message(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    )

    title_template: TitleTemplate = TitleTemplate("Concepts from {title}")

    template: MessageTemplate = MessageTemplate(
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
    )

    windowing: WindowSettings = WINDOW_64_PARA

    def run_item(self, item: Item) -> Item:
        item = llm_transform_item(self.context(), item)
        item.body = as_bullet_points(concepts_from_markdown(not_none(item.body)))
        return item
