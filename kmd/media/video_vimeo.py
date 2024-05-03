import tempfile
import logging
import os
from typing import Optional
from urllib.parse import urlparse
from pydub import AudioSegment
from vimeo_downloader import Vimeo as VimeoDownloader

from kmd.media.media_services import VideoService

log = logging.getLogger(__name__)


class Vimeo(VideoService):
    def canonicalize(self, url: str) -> Optional[str]:
        parsed_url = urlparse(url)
        if parsed_url.hostname == "vimeo.com":
            video_id = parsed_url.path[1:]
            if not video_id:
                return None
            return f"https://vimeo.com/{video_id}"
        else:
            return None

    def download_audio(self, url: str) -> str:
        temp_dir = tempfile.mkdtemp()
        v = VimeoDownloader(url)
        stream = v.streams[0]  # Pick the worst quality for smaller file size.
        video_path = stream.download(download_directory=temp_dir, filename="video.mp4", mute=True)

        mp3_path = os.path.join(temp_dir, "extracted_audio.mp3")
        log.info("Extracting audio from Vimeo video %s at %s to %s", url, video_path, mp3_path)
        audio = AudioSegment.from_file(video_path, format="mp4")
        audio.export(mp3_path, format="mp3")

        return mp3_path
