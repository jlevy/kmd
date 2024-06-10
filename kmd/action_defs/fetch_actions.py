from kmd.action_exec.action_registry import kmd_action
from kmd.media import web
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    EachItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item
from kmd.util.type_utils import not_none
from kmd.config.logger import get_logger

log = get_logger(__name__)


@kmd_action
class FetchPage(EachItemAction):
    def __init__(self):
        super().__init__(
            name="fetch_page",
            friendly_name="Fetch Page Details",
            description="Fetches the title, description, and body of a web page.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput(f"Item must have a URL: {item}")

        page_data = web.fetch_extract(not_none(item.url))
        fetched_item = item.new_copy_with(
            title=page_data.title, description=page_data.description, body=page_data.content
        )

        return fetched_item
