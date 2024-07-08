import tempfile
import os
from typing import Optional
from urllib.parse import urlparse
from pydub import AudioSegment
from vimeo_downloader import Vimeo as VimeoDownloader
from kmd.model.media_model import MediaMetadata, MediaService
from kmd.util.url import Url
from kmd.config.logger import get_logger

log = get_logger(__name__)


class Vimeo(MediaService):
    def get_id(self, url: Url) -> Optional[str]:
        parsed_url = urlparse(url)
        if parsed_url.hostname == "vimeo.com":
            video_id = parsed_url.path[1:]
            if video_id:
                return video_id
        return None

    def metadata(self, url: Url) -> MediaMetadata:
        raise NotImplementedError()

    def canonicalize(self, url: Url) -> Optional[str]:
        video_id = self.get_id(url)
        if video_id:
            return f"https://vimeo.com/{video_id}"
        return None

    def thumbnail_url(self, url: Url) -> Optional[Url]:
        raise NotImplementedError()

    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        raise NotImplementedError()  # TODO

    def download_audio(self, url: Url) -> str:
        temp_dir = tempfile.mkdtemp()
        v = VimeoDownloader(url)
        stream = v.streams[0]  # Pick the worst quality for smaller file size.
        video_path = stream.download(download_directory=temp_dir, filename="video.mp4", mute=True)

        mp3_path = os.path.join(temp_dir, "extracted_audio.mp3")
        log.info("Extracting audio from Vimeo video %s at %s to %s", url, video_path, mp3_path)
        audio = AudioSegment.from_file(video_path, format="mp4")
        audio.export(mp3_path, format="mp3")

        return mp3_path
