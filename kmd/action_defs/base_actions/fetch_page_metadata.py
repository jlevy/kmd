from kmd.exec.action_registry import kmd_action
from kmd.media import web
from kmd.media.media_services import get_media_metadata
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    EachItemAction,
)
from kmd.model.errors_model import InvalidInput, WebFetchError
from kmd.model.items_model import Item
from kmd.config.logger import get_logger

log = get_logger(__name__)


@kmd_action
class FetchPageMetadata(EachItemAction):
    def __init__(self):
        super().__init__(
            name="fetch_page_metadata",
            description="Fetches a web page for title, description, and thumbnail, if available.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput(f"Item must have a URL: {item}")

        # Prefer fetching metadata from the video if possible.
        # Data is cleaner and YouTube for example often blocks regular scraping.
        media_metadata = get_media_metadata(item.url)
        if media_metadata:
            fetched_item = Item.from_media_metadata(media_metadata)
            fetched_item = item.merged_copy(fetched_item)
        else:
            page_data = web.fetch_extract(item.url)
            fetched_item = item.new_copy_with(
                title=page_data.title or item.title,
                description=page_data.description or item.description,
                thumbnail_url=page_data.thumbnail_url or item.thumbnail_url,
            )

        if not fetched_item.title:
            raise WebFetchError(f"Failed to fetch page data: title is missing: {item.url}")

        return fetched_item
