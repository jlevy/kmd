import logging
import tempfile
import os
from typing import Optional
from urllib.parse import urlparse, parse_qs
import yt_dlp
from .media_services import VideoService

log = logging.getLogger(__name__)


class YouTube(VideoService):
    def canonicalize(self, url: str) -> Optional[str]:
        parsed_url = urlparse(url)
        if parsed_url.hostname == "youtu.be":
            video_id = parsed_url.path[1:]
        elif parsed_url.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
            query = parse_qs(parsed_url.query)
            video_id = query.get("v", [""])[0]
        else:
            return None
        if not video_id:
            return None
        return f"https://www.youtube.com/watch?v={video_id}"

    def download_audio(self, url: str, target_dir: Optional[str] = None) -> str:
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
