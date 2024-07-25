from kmd.media.media_services import download_audio
from kmd.action_exec.action_registry import kmd_action
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    EachItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item
from kmd.config.logger import get_logger

log = get_logger(__name__)


@kmd_action
class DownloadMedia(EachItemAction):
    def __init__(self):
        super().__init__(
            name="download_media",
            description="Download and save audio from a podcast or video. Only saves to media cache; does not create new items.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput("Item must have a URL")

        download_audio(item.url)

        # Just return the same item since the video is now saved to cache.
        return item
