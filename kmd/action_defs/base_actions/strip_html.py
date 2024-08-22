from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import (
    CachedItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import has_text_body
from kmd.text_formatting.text_formatting import html_to_plaintext

log = get_logger(__name__)


@kmd_action()
class StripHtml(CachedItemAction):
    def __init__(self):
        super().__init__(
            name="strip_html",
            description="Strip HTML tags from text or Markdown.",
            precondition=has_text_body,
        )

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput(f"Item must have a body: {item}")

        clean_body = html_to_plaintext(item.body)
        output_item = item.derived_copy(
            type=ItemType.note,
            format=Format.markdown,
            body=clean_body,
        )

        return output_item
