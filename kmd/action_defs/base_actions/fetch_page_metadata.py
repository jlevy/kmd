from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.media.media_services import get_media_metadata
from kmd.model import Item, PerItemAction, Precondition
from kmd.preconditions.precondition_defs import is_url_item
from kmd.web_content.web_extract import fetch_extract

log = get_logger(__name__)


@kmd_action
class FetchPageMetadata(PerItemAction):

    name: str = "fetch_page_metadata"

    description: str = """
        Fetches a web page for title, description, and thumbnail, if available.
        """

    precondition: Precondition = is_url_item

    cacheable: bool = False

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
            # cache_path, _was_cached = cache_file(item.url)  # FIXME: Handle all file formats.

            page_data = fetch_extract(item.url)
            fetched_item = item.new_copy_with(
                title=page_data.title or item.title,
                description=page_data.description or item.description,
                thumbnail_url=page_data.thumbnail_url or item.thumbnail_url,
            )

        if not fetched_item.title:
            log.warning("Failed to fetch page data: title is missing: %s", item.url)

        return fetched_item
