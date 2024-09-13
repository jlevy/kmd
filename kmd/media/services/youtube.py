import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from kmd.config.logger import get_logger
from kmd.config.text_styles import EMOJI_WARN
from kmd.errors import ApiResultError, InvalidInput
from kmd.file_formats.yaml_util import to_yaml_string
from kmd.media.yt_dlp_utils import parse_date, ydl_download_media, ydl_extract_info
from kmd.model.media_model import (
    HeatmapValue,
    MediaFormat,
    MediaMetadata,
    MediaService,
    MediaUrlType,
    SERVICE_YOUTUBE,
)
from kmd.util.type_utils import not_none
from kmd.util.url import Url

log = get_logger(__name__)


VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


class YouTube(MediaService):
    def get_media_id(self, url: Url) -> Optional[str]:
        parsed_url = urlparse(url)
        if parsed_url.hostname == "youtu.be":
            video_id = parsed_url.path[1:]
            if VIDEO_ID_PATTERN.match(video_id):
                return video_id
        elif parsed_url.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
            query = parse_qs(parsed_url.query)
            video_id = query.get("v", [""])[0]
            if video_id and VIDEO_ID_PATTERN.match(video_id):
                return video_id
        return None

    def canonicalize_and_type(self, url: Url) -> Tuple[Optional[Url], Optional[MediaUrlType]]:
        parsed_url = urlparse(url)
        if parsed_url.hostname == "youtu.be":
            video_id = self.get_media_id(url)
            if video_id:
                return Url(f"https://www.youtube.com/watch?v={video_id}"), MediaUrlType.video
        elif parsed_url.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
            # Check for channel URLs:
            if (
                "/channel/" in parsed_url.path
                or "/c/" in parsed_url.path
                or "/user/" in parsed_url.path
                or parsed_url.path.startswith("/@")
            ):
                # It's already a canonical channel URL.
                return url, MediaUrlType.channel

            query = parse_qs(parsed_url.query)

            # Check for playlist URLs:
            if "/playlist" in parsed_url.path:
                list_id = query.get("list", [""])[0]
                return (
                    Url(f"https://www.youtube.com/playlist?list={list_id}"),
                    MediaUrlType.playlist,
                )

            # Check for video URLs:
            video_id = self.get_media_id(url)
            if video_id:
                return Url(f"https://www.youtube.com/watch?v={video_id}"), MediaUrlType.video

        return None, None

    def thumbnail_url(self, url: Url) -> Optional[Url]:
        id = self.get_media_id(url)
        return Url(f"https://img.youtube.com/vi/{id}/sddefault.jpg") if id else None
        # Others:
        # https://img.youtube.com/vi/{id}/hqdefault.jpg
        # https://img.youtube.com/vi/{id}/maxresdefault.jpg

    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        canon_url = self.canonicalize(url)
        if not canon_url:
            raise InvalidInput(f"Unrecognized YouTube URL: {url}")
        return Url(canon_url + f"&t={timestamp}s")

    def download_media(self, url: Url, target_dir: Path) -> Dict[MediaFormat, Path]:
        url = not_none(self.canonicalize(url), "Not a recognized YouTube URL")
        return ydl_download_media(url, target_dir, include_video=True)

    def _extract_info(self, url: Url) -> Dict[str, Any]:
        url = not_none(self.canonicalize(url), "Not a recognized YouTube URL")
        return ydl_extract_info(url)

    def metadata(self, url: Url, full: bool = False) -> MediaMetadata:
        url = not_none(self.canonicalize(url), "Not a recognized YouTube URL")
        yt_result: Dict[str, Any] = self._extract_info(url)

        return self._parse_metadata(yt_result, full=full)

    def list_channel_items(self, url: Url) -> List[MediaMetadata]:
        """
        Get all video URLs and metadata from a YouTube channel or playlist.
        """

        result = self._extract_info(url)

        if "entries" in result:
            entries = result["entries"]
        else:
            log.warning("%s No videos found in the channel.", EMOJI_WARN)
            entries = []

        video_meta_list: List[MediaMetadata] = []

        # TODO: Inspect and collect rest of the metadata here, like upload date etc.
        for value in entries:
            if "entries" in value:
                # For channels there is a list of values each with their own videos.
                video_meta_list.extend(self._parse_metadata(e) for e in value["entries"])
            else:
                # For playlists, entries holds the videos.
                video_meta_list.append(self._parse_metadata(value))

        log.message("Found %d videos in channel %s", len(video_meta_list), url)

        return video_meta_list

    def _parse_metadata(
        self, yt_result: Dict[str, Any], full: bool = False, **overrides: Dict[str, Any]
    ) -> MediaMetadata:
        try:
            media_id = yt_result["id"]  # Renamed for clarity.
            if not media_id:
                raise KeyError("No ID found")

            url = yt_result.get("webpage_url") or yt_result.get("url")
            if not url:
                raise KeyError("No URL found")

            thumbnail_url = self.thumbnail_url(Url(url))
            # thumbnail_url = best_thumbnail(yt_result)  # Alternate approach, but messier.

            # Apparently upload_date is in full video metadata but not channel metadata.
            upload_date_str = yt_result.get("upload_date")
            upload_date = parse_date(upload_date_str) if upload_date_str else None

            # Heatmap is interesting but verbose so skipping by default.
            heatmap = None
            if full:
                heatmap = [HeatmapValue(**h) for h in yt_result.get("heatmap", [])] or None

            result = MediaMetadata(
                media_id=media_id,
                media_service=SERVICE_YOUTUBE,
                url=url,
                thumbnail_url=thumbnail_url,
                title=yt_result["title"],
                description=yt_result["description"],
                upload_date=upload_date,
                channel_url=Url(yt_result["channel_url"]),
                view_count=yt_result.get("view_count"),
                duration=yt_result.get("duration"),
                heatmap=heatmap,
                **overrides,
            )
            log.message("Parsed YouTube metadata: %s", result)
        except KeyError as e:
            log.error("Missing key in YouTube metadata (see saved object): %s", e)
            log.save_object(
                "yt_dlp result", None, to_yaml_string(yt_result, stringify_unknown=True)
            )
            raise ApiResultError("Did not find key in YouTube metadata: %s" % e)

        return result


def best_thumbnail(data: Dict[str, Any]) -> Optional[Url]:
    """
    Get the best thumbnail from YouTube metadata, which is of the form:
    {
        'thumbnails': [
            {'url': 'https://i.ytimg.com/vi/gc417NquXbk/hqdefault.jpg?sqp=-oaymwEbCKgBEF5IVfKriqkDDggBFQAAiEIYAXABwAEG&rs=AOn4CLC7F70CUSkwqkrgEwKX1AmXCJ8jsQ', 'height': 94, 'width': 168},
            {'url': 'https://i.ytimg.com/vi/gc417NquXbk/hqdefault.jpg?sqp=-oaymwEbCMQBEG5IVfKriqkDDggBFQAAiEIYAXABwAEG&rs=AOn4CLA6pIOQRUlixQogTAR0NAv3zJgxqQ', 'height': 110, 'width': 196},
            {'url': 'https://i.ytimg.com/vi/gc417NquXbk/hqdefault.jpg?sqp=-oaymwEcCPYBEIoBSFXyq4qpAw4IARUAAIhCGAFwAcABBg==&rs=AOn4CLC7zW8Hu59MgQkRPX4WsVpc-tkxxQ', 'height': 138, 'width': 246},
            {'url': 'https://i.ytimg.com/vi/gc417NquXbk/hqdefault.jpg?sqp=-oaymwEcCNACELwBSFXyq4qpAw4IARUAAIhCGAFwAcABBg==&rs=AOn4CLB7nBpvNKwCwrtr_lv85T0GITOFjA', 'height': 188, 'width': 336},
        ],
    }
    """
    thumbnail_url = None
    try:
        thumbnails = data["thumbnails"]
        if not isinstance(thumbnails, list):
            return None
        largest_thumbnail = max(thumbnails, key=lambda x: x.get("width", 0))
        thumbnail_url = largest_thumbnail.get("url", None)
    except (KeyError, TypeError):
        pass

    if not thumbnail_url:
        thumbnail_url = data.get("thumbnail")

    return Url(thumbnail_url) if thumbnail_url else None


## Tests


def test_canonicalize_youtube():
    youtube = YouTube()

    def assert_canon(url: str, canon_url: str):
        assert youtube.canonicalize(Url(url)) == Url(canon_url)

    assert_canon("https://youtu.be/12345678901", "https://www.youtube.com/watch?v=12345678901")

    assert_canon(
        "https://www.youtube.com/watch?v=12345678901", "https://www.youtube.com/watch?v=12345678901"
    )

    assert_canon(
        "https://www.youtube.com/watch?v=_5y0AalUDh4&list=PL9XbNw3iJu1zKJRyV3Jz3rqlFV1XJfvNv&index=12",
        "https://www.youtube.com/watch?v=_5y0AalUDh4",
    )

    assert_canon(
        "https://www.youtube.com/@hubermanlab",
        "https://www.youtube.com/@hubermanlab",
    )

    assert_canon(
        "https://youtube.com/playlist?list=PLPNW_gerXa4N_PVVoq0Za03YKASSGCazr&si=9IVO8p-ZwmMLI18F",
        "https://www.youtube.com/playlist?list=PLPNW_gerXa4N_PVVoq0Za03YKASSGCazr",
    )
