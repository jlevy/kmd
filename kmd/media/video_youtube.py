import re
import tempfile
import os
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass, fields
from pprint import pprint
import yt_dlp
from kmd.text_ui.text_styles import EMOJI_WARN
from kmd.model.errors_model import ApiResultError, InvalidInput
from kmd.util.type_utils import not_none
from kmd.util.url import Url
from .media_services import VideoService
from kmd.config.logger import get_logger

log = get_logger(__name__)


VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


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
        except TypeError:
            print(pprint(data))
            raise ApiResultError(f"Invalid data for YoutubeVideoMeta: {data}")


class YouTube(VideoService):
    def get_id(self, url: Url) -> Optional[str]:
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

    def canonicalize(self, url: Url) -> Optional[Url]:
        parsed_url = urlparse(url)
        if parsed_url.hostname == "youtu.be":
            video_id = self.get_id(url)
            if video_id:
                return Url(f"https://www.youtube.com/watch?v={video_id}")
        elif parsed_url.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
            # Check for channel URLs:
            if (
                "/channel/" in parsed_url.path
                or "/c/" in parsed_url.path
                or "/user/" in parsed_url.path
                or parsed_url.path.startswith("/@")
            ):
                return url  # It's already a canonical channel URL.

            query = parse_qs(parsed_url.query)

            # Check for playlist URLs:
            if "/playlist" in parsed_url.path:
                list_id = query.get("list", [""])[0]
                return Url(f"https://www.youtube.com/playlist?list={list_id}")

            # Check for video URLs:
            video_id = self.get_id(url)
            if video_id:
                return Url(f"https://www.youtube.com/watch?v={video_id}")

    def timestamp_url(self, url: Url, timestamp: float) -> str:
        canon_url = self.canonicalize(url)
        if not canon_url:
            raise InvalidInput(f"Unrecognized YouTube URL: {url}")
        return canon_url + f"&t={timestamp}s"

    def download_audio(self, url: Url, target_dir: Optional[str] = None) -> str:
        """Download and convert to mp3 using yt_dlp, which seems like the best library for this."""

        temp_dir = target_dir or tempfile.mkdtemp()
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(temp_dir, "audio.%(id)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        log.info("Extracting audio from YouTube video %s at %s", url, temp_dir)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            audio_file_path = ydl.prepare_filename(info_dict)

        # yt_dlp returns the .webm file, so this is the converted .mp3.
        mp3_path = os.path.splitext(audio_file_path)[0] + ".mp3"
        return mp3_path

    def list_channel_videos(self, url: Url) -> List[YoutubeVideoMeta]:
        """
        Get all video URLs and metadata from a YouTube channel or playlist.
        """

        ydl_opts = {
            "extract_flat": "in_playlist",  # Extract metadata only, without downloading.
            "quiet": True,
            "dump_single_json": True,
        }

        url = not_none(self.canonicalize(url), "Not a recognized YouTube URL")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(str(url), download=False)
            log.save_object("yt_dlp result", "yt_dlp_result", result)

        if not isinstance(result, dict):
            raise ApiResultError(f"Unexpected result from yt_dlp: {result}")
        if "entries" in result:
            entries = result["entries"]
        else:
            log.warning("%s No videos found in the channel.", EMOJI_WARN)
            entries = []

        video_meta_list = []

        # TODO: Inspect and collect rest of the metadata here, like upload date etc.
        for value in entries:
            if "entries" in value:
                # For channels there is a list of values each with their own videos.
                video_meta_list.extend(YoutubeVideoMeta.from_dict(e) for e in value["entries"])
            else:
                # For playlists, entries holds the videos.
                video_meta_list.append(YoutubeVideoMeta.from_dict(value))

        log.message("Found %d videos in channel %s", len(video_meta_list), url)

        return video_meta_list


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
    try:
        thumbnails = data["thumbnails"]
        if not isinstance(thumbnails, list):
            return None
        largest_thumbnail = max(thumbnails, key=lambda x: x.get("width", 0))
        url_str = largest_thumbnail.get("url", None)
        return Url(url_str) if url_str else None
    except (KeyError, TypeError):
        return None


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
