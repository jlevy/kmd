from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.model import Item, ItemType, PerItemAction
from kmd.preconditions.precondition_defs import has_html_body, has_text_body
from kmd.text_formatting.html_find_tags import html_find_tag
from kmd.util.string_replace import replace_multiple

log = get_logger(__name__)


@kmd_action
class RemoveSpeakerLabels(PerItemAction):
    def __init__(self):
        super().__init__(
            name="remove_speaker_labels",
            description="""
            Remove speaker labels (<span data-speaker-id=...>...</span>)
            from the transcript. Handy when the transcription has added them
            erroneously.
            """,
            precondition=has_html_body | has_text_body,
        )

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput("Item must have a body")

        # Find all <span data-speaker-id=...>...</span> elements.
        matches = html_find_tag(item.body, tag_name="span", attr_name="data-speaker-id")

        # Prepare replacements to remove these elements.
        replacements = []
        for match in matches:
            replacements.append((match.start_offset, match.end_offset, ""))

        # Remove the speaker labels from the body.
        new_body = replace_multiple(item.body, replacements)

        # Create a new item with the cleaned body with same doc type and format.
        output_item = item.derived_copy(type=ItemType.doc, body=new_body)

        return output_item
