import re
import tempfile
import os
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs
from datetime import date
import yt_dlp
from kmd.file_storage.yaml_util import to_yaml_string
from kmd.text_ui.text_styles import EMOJI_WARN
from kmd.model.errors_model import ApiResultError, InvalidInput
from kmd.util.log_calls import log_calls
from kmd.util.type_utils import not_none
from kmd.util.url import Url
from kmd.model.media_model import SERVICE_YOUTUBE, HeatmapValue, MediaMetadata, MediaService
from kmd.config.logger import get_logger

log = get_logger(__name__)


VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


@log_calls(level="message", show_return=True)
def parse_date(upload_date: str | date) -> date:
    if isinstance(upload_date, str):
        return date.fromisoformat(upload_date)
    elif isinstance(upload_date, date):
        return upload_date
    raise ValueError(f"Invalid date: {upload_date}")


class YouTube(MediaService):
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

    def thumbnail_url(self, url: Url) -> Optional[Url]:
        id = self.get_id(url)
        return Url(f"https://img.youtube.com/vi/{id}/sddefault.jpg") if id else None
        # Others:
        # https://img.youtube.com/vi/{id}/hqdefault.jpg
        # https://img.youtube.com/vi/{id}/maxresdefault.jpg

    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        canon_url = self.canonicalize(url)
        if not canon_url:
            raise InvalidInput(f"Unrecognized YouTube URL: {url}")
        return Url(canon_url + f"&t={timestamp}s")

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

    def _extract_info(self, url: Url) -> Dict[str, Any]:
        ydl_opts = {
            "extract_flat": "in_playlist",  # Extract metadata only, without downloading.
            "quiet": True,
            "dump_single_json": True,
        }

        url = not_none(self.canonicalize(url), "Not a recognized YouTube URL")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(str(url), download=False)

            log.save_object("yt_dlp result", None, to_yaml_string(result, stringify_unknown=True))

            if not isinstance(result, dict):
                raise ApiResultError(f"Unexpected result from yt_dlp: {result}")

            return result

    def metadata(self, url: Url, full: bool = False) -> MediaMetadata:
        """
        Get metadata for a YouTube video.
        """
        url = not_none(self.canonicalize(url), "Not a recognized YouTube URL")
        yt_result: Dict[str, Any] = self._extract_info(url)

        return self._parse_metadata(yt_result, full=full)

    def list_channel_videos(self, url: Url) -> List[MediaMetadata]:
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
