from kmd.media.video import video_download_audio
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
class DownloadVideo(EachItemAction):
    def __init__(self):
        super().__init__(
            name="download_video",
            description="Download and extract audio from a video. Only saves to media cache; does not create new items.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput("Item must have a URL")

        video_download_audio(item.url)

        # Actually return the same item since the video is actually saved to cache.
        return item
