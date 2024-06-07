from kmd.media.video import video_download_audio, youtube
from kmd.actions.action_registry import kmd_action
from kmd.media.video import video_transcription
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    Action,
    ActionInput,
    ActionResult,
    EachItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import UNTITLED, FileExt, Format, Item, ItemType
from kmd.util.url import Url
from kmd.config.logger import get_logger

log = get_logger(__name__)


@kmd_action
class ListChannelVideos(Action):
    def __init__(self):
        super().__init__(
            name="list_channel_videos",
            friendly_name="List Channel Videos",
            description="Get the URL of every video in the given channel. YouTube only for now.",
        )

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        if not item.url:
            raise InvalidInput("Item must have a URL")
        if not youtube.canonicalize(item.url):
            raise InvalidInput("Only YouTube download currently supported")

        video_meta_list = youtube.list_channel_videos(item.url)

        result_items = []
        for info in video_meta_list:
            if not youtube.canonicalize(Url(info.url)):
                log.warning("Skipping non-recognized video URL: %s", info.url)
                continue

            item = Item(
                ItemType.resource,
                format=Format.url,
                url=Url(info.url),
                title=info.title,
                description=info.description,
                extra={
                    "youtube_metadata": {
                        "id": info.id,
                        "thumbnails": info.thumbnails,
                        "view_count": info.view_count,
                    }
                },
            )

            result_items.append(item)

        return ActionResult(result_items)


@kmd_action
class DownloadVideo(EachItemAction):
    def __init__(self):
        super().__init__(
            name="download_video",
            friendly_name="Download Video",
            description="Download and extract audio from a video. Only saves to media cache; does not create new items.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput("Item must have a URL")

        video_download_audio(item.url)

        # Actually return the same item since the video is actually saved to cache.
        return item


@kmd_action
class TranscribeVideo(EachItemAction):
    def __init__(self):
        super().__init__(
            name="transcribe_video",
            friendly_name="Transcribe Video",
            description="Download and transcribe audio from a video.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput("Item must have a URL")

        transcription = video_transcription(item.url)
        title = item.title or UNTITLED  # This shouldn't happen normally.
        result_title = f"{title} (transcription)"
        result_item = item.derived_copy(
            type=ItemType.note,
            title=result_title,
            body=transcription,
            format=Format.md_html,  # Important to note this since we put in timestamp spans.
            file_ext=FileExt.md,
        )

        return result_item
