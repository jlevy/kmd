from kmd.media.media_download import download_audio
from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    ForEachItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import is_url

log = get_logger(__name__)


@kmd_action
class DownloadMedia(ForEachItemAction):
    def __init__(self):
        super().__init__(
            name="download_media",
            description="Download and save audio from a podcast or video. Only saves to media cache; does not create new items.",
            expected_args=ONE_OR_MORE_ARGS,
            precondition=is_url,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput("Item must have a URL")

        download_audio(item.url)

        # Just return the same item since the video is now saved to cache.
        return item
