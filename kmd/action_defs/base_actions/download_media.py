from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.media.media_tools import cache_media
from kmd.model import Item, PerItemAction
from kmd.preconditions.precondition_defs import is_url

log = get_logger(__name__)


@kmd_action
class DownloadMedia(PerItemAction):
    def __init__(self):
        super().__init__(
            name="download_media",
            description="Download and save audio from a podcast or video. Only saves to media cache; does not create new items.",
            precondition=is_url,
            cachable=False,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput("Item must have a URL")

        cache_media(item.url)

        # Just return the same item since the video is now saved to cache.
        return item
