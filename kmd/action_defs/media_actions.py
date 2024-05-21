from dataclasses import dataclass, fields
from pprint import pprint
from typing import Any, Dict, List
from kmd.file_storage.workspaces import current_workspace
from kmd.media.video import video_download_audio, youtube
from kmd.actions.action_registry import register_action
from kmd.media import web
from kmd.media.video import video_transcription
from kmd.model.actions_model import ONE_OR_MORE_ARGS, Action, ActionInput, ActionResult
from kmd.model.items_model import FileExt, Format, Item, ItemType
from kmd.util.type_utils import not_none
from kmd.util.url import Url
from kmd.config.logger import get_logger

log = get_logger(__name__)


@register_action
class FetchPage(Action):
    def __init__(self):
        super().__init__(
            name="fetch_page",
            friendly_name="Fetch Page Details",
            description="Fetches the title, description, and body of a web page.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run(self, items: ActionInput) -> ActionResult:
        for item in items:
            if not item.url:
                raise ValueError(f"Item must have a URL: {item}")

        result_items = []
        for item in items:
            page_data = web.fetch_extract(not_none(item.url))
            fetched_item = item.new_copy_with(
                title=page_data.title, description=page_data.description, body=page_data.content
            )
            current_workspace().save(fetched_item)
            result_items.append(fetched_item)

        return ActionResult(result_items, replaces_input=True)


@dataclass
class YoutubeVideoMeta:
    id: str
    url: str
    title: str
    description: str
    thumbnails: List[Dict]
    view_count: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "YoutubeVideoMeta":
        try:
            field_names = {f.name for f in fields(cls)}
            filtered_data = {k: v for k, v in data.items() if k in field_names}
            return cls(**filtered_data)
        except TypeError as e:
            print(pprint(data))
            raise ValueError(f"Invalid data for YoutubeVideoMeta: {data}")


@register_action
class ListChannelVideos(Action):
    def __init__(self):
        super().__init__(
            name="list_channel_videos",
            friendly_name="List Channel Videos",
            description="Get the URL of every video in the given channel. YouTube only for now.",
        )

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        url = item.url
        if not url:
            raise ValueError("Item must have a URL")
        if not youtube.canonicalize(url):
            raise ValueError("Only YouTube download currently supported")

        result_raw = youtube.list_channel_videos(url)

        video_meta_list = []
        for page in result_raw:
            video_meta_list.extend(YoutubeVideoMeta.from_dict(info) for info in page["entries"])
        log.message("Found %d videos in channel %s", len(video_meta_list), url)

        result_items = []
        for info in video_meta_list:
            if not youtube.canonicalize(info.url):
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

            current_workspace().save(item)
            result_items.append(item)

        return ActionResult(result_items)


@register_action
class DownloadVideo(Action):
    def __init__(self):
        super().__init__(
            name="download_video",
            friendly_name="Download Video",
            description="Download and extract audio from a video. Only saves to media cache; does not create new items.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run(self, items: ActionInput) -> ActionResult:
        result_items = []
        for item in items:
            url = item.url
            if not url:
                raise ValueError("Item must have a URL")

            video_download_audio(url)

            # Actually return the same item since the video is actually saved to cache.
            result_items.append(item)

        return ActionResult(result_items)


@register_action
class TranscribeVideo(Action):
    def __init__(self):
        super().__init__(
            name="transcribe_video",
            friendly_name="Transcribe Video",
            description="Download and transcribe audio from a video.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run(self, items: ActionInput) -> ActionResult:
        result_items = []
        for item in items:
            url = item.url
            if not url:
                raise ValueError("Item must have a URL")

            transcription = video_transcription(url)
            result_title = f"{item.title} (transcription)"
            result_item = item.new_copy_with(
                type=ItemType.note,
                title=result_title,
                body=transcription,
                format=Format.markdown,
                file_ext=FileExt.md,
            )
            current_workspace().save(result_item)

            result_items.append(result_item)

        return ActionResult(result_items)
