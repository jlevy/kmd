import re
import tempfile
import os
from typing import Optional, List, Dict
from urllib.parse import urlparse, parse_qs
import yt_dlp
from kmd.util.url import Url
from .media_services import VideoService
from kmd.config.logger import get_logger

log = get_logger(__name__)


VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


class YouTube(VideoService):
    def canonicalize(self, url: Url) -> Optional[Url]:
        parsed_url = urlparse(url)
        if parsed_url.hostname == "youtu.be":
            video_id = parsed_url.path[1:]
            if VIDEO_ID_PATTERN.match(video_id):
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
            video_id = query.get("v", [""])[0]
            if video_id and VIDEO_ID_PATTERN.match(video_id):
                return Url(f"https://www.youtube.com/watch?v={video_id}")

        return None

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

    def list_channel_videos(self, channel_url: Url) -> List[Dict]:
        """Get all video URLs and metadata from a YouTube channel."""

        ydl_opts = {
            "extract_flat": "in_playlist",  # Extract metadata only, without downloading.
            "quiet": True,
            "dump_single_json": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(str(channel_url), download=False)

        if not isinstance(result, dict):
            raise ValueError(f"Unexpected result from yt_dlp: {result}")
        if "entries" in result:
            videos = result["entries"]
            return videos
        else:
            log.warning("No videos found in the channel.")
            return []


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
