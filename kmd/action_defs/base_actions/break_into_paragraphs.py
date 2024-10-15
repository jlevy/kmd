from kmd.config.logger import get_logger
from kmd.errors import NoMatch
from kmd.exec.action_registry import kmd_action
from kmd.model import DEFAULT_FAST_LLM, Item, LLM, LLMAction, Message, MessageTemplate
from kmd.preconditions.precondition_defs import has_speaker_ids
from kmd.provenance.source_items import find_upstream_item
from kmd.text_docs.diff_filters import changes_whitespace
from kmd.text_docs.text_diffs import DiffFilter
from kmd.text_docs.window_settings import WINDOW_2K_WORDTOKS, WindowSettings

log = get_logger(__name__)


@kmd_action
class BreakIntoParagraphs(LLMAction):

    name: str = "break_into_paragraphs"

    description: str = (
        "Reformat text as paragraphs. Perserves all text exactly except for whitspace changes."
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
        try:
            multi_speakers_item = find_upstream_item(item, has_speaker_ids)
            # Usually not worth editing a transcript into paragraphs if it has multiple speakers.
            log.warning(
                "Skipping break_into_paragraphs for doc as it has multiple speakers: %s",
                multi_speakers_item,
            )
            return item
        except NoMatch:
            return super().run_item(item)
