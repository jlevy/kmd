from dataclasses import asdict, dataclass
from typing import List
from kmd.config.logger import get_logger
from kmd.file_storage.yaml_util import to_yaml_string
from kmd.lang_tools.clean_headings import clean_heading, summary_heading
from kmd.media.video import get_video_id
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
from kmd.preconditions.common_preconditions import is_youtube_video
from kmd.provenance.source_items import find_upstream_item
from kmd.util.type_utils import as_dataclass
from kmd.web_gen.template_render import render_web_template

log = get_logger(__name__)


@dataclass
class VideoInfo:
    youtube_id: str
    title: str
    description: str
    topics: List[str]


@dataclass
class VideoGallery:
    title: str
    videos: List[VideoInfo]


def video_gallery_config(items: List[Item]) -> Item:
    """
    Get an item with the config for a video gallery.
    """
    videos = []
    for item in items:
        source_item = find_upstream_item(item, is_youtube_video)

        youtube_id = get_video_id(source_item.url)
        log.message(
            "Pulling video from source item: %s: %s", source_item.store_path, source_item.url
        )
        if not youtube_id or not is_youtube_video(source_item):
            raise InvalidInput(f"Item must be a YouTube URL with id: {source_item}")

        video_info = VideoInfo(
            youtube_id=youtube_id,
            title=clean_heading(item.abbrev_title()),
            description=item.abbrev_description(),
            topics=[],  # TODO
        )
        videos.append(video_info)

    title = summary_heading([video.title for video in videos])
    gallery = VideoGallery(title=title, videos=videos)

    config_item = Item(
        title=f"Config for {title}",
        type=ItemType.config,
        format=Format.yaml,
        body=to_yaml_string(asdict(gallery)),
    )
    return config_item


def video_gallery_generate(config_item: Item) -> str:
    """
    Generate a video gallery web page using the supplied config.
    """
    config = config_item.read_as_config()
    video_gallery = as_dataclass(config, VideoGallery)  # Checks the format.

    content = render_web_template("youtube_gallery.template.html", asdict(video_gallery))

    return render_web_template(
        "base_webpage.template.html", {"title": video_gallery.title, "content": content}
    )
