from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.model import Format, Item, ItemType, PerItemAction
from kmd.preconditions.precondition_defs import has_html_body, has_text_body
from kmd.util.format_utils import html_to_plaintext

log = get_logger(__name__)


@kmd_action
class StripHtml(PerItemAction):
    def __init__(self):
        super().__init__(
            name="strip_html",
            description="Strip HTML tags from HTML or Markdown.",
            precondition=has_html_body | has_text_body,
        )

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput("Item must have a body")

        clean_body = html_to_plaintext(item.body)
        output_item = item.derived_copy(
            type=ItemType.doc,
            format=Format.markdown,
            body=clean_body,
        )

        return output_item
