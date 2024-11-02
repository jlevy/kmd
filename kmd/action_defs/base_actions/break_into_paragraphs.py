from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import DEFAULT_FAST_LLM, Item, LLM, LLMAction, Message, MessageTemplate
from kmd.text_docs.diff_filters import changes_whitespace
from kmd.text_docs.text_doc import TextDoc
from kmd.text_docs.token_diffs import DiffFilter
from kmd.text_docs.window_settings import WINDOW_2K_WORDTOKS, WindowSettings

log = get_logger(__name__)


@kmd_action
class BreakIntoParagraphs(LLMAction):

    name: str = "break_into_paragraphs"

    description: str = (
        "Reformat text as paragraphs. Preserves all text exactly except for whitespace changes."
    )

    system_message: Message = Message(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    )

    template: MessageTemplate = MessageTemplate(
        """
        Format this text according to these rules:

        - Break the following text into paragraphs so it is readable and organized.

        - Add a paragraph break whenever the topic changes.

        - Paragraphs can be short or up to several sentences long.

        - Do *not* change any words of the text. Add line breaks only.

        - Preserve all Markdown formatting.

        - ONLY GIVE THE FORMATTED TEXT, with no other commentary.

        Original text:

        {body}

        Formatted text:
        """
    )

    model: LLM = DEFAULT_FAST_LLM

    diff_filter: DiffFilter = changes_whitespace

    windowing: WindowSettings = WINDOW_2K_WORDTOKS

    def run_item(self, item: Item) -> Item:
        if not item.body:
            return item

        # Check each paragraph's sentence count to see if we need to do this.
        MAX_SENTENCES_PER_PARAGRAPH = 7
        doc = TextDoc.from_text(item.body)
        log.message("Doc size: %s", doc.size_summary())
        biggest_para = max(doc.paragraphs, key=lambda p: len(p.sentences))
        can_skip = len(biggest_para.sentences) <= MAX_SENTENCES_PER_PARAGRAPH

        log.message(
            "Checking if we need to break into paragraphs: "
            "biggest paragraph has %d sentences vs max of %d so %s",
            len(biggest_para.sentences),
            MAX_SENTENCES_PER_PARAGRAPH,
            "can skip" if can_skip else "must run",
        )
        if can_skip:
            return item
        else:
            return super().run_item(item)
