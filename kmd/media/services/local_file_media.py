import os
import shlex
import subprocess  # Add this import
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from strif import copyfile_atomic
from kmd.model.errors_model import FileNotFound, InvalidInput
from kmd.model.file_formats_model import FileExt, parse_file_format
from kmd.shell_tools.native_tools import CmdlineTool, tool_check
from kmd.text_formatting.text_formatting import fmt_path
from kmd.util.url import Url
from kmd.model.media_model import (
    MediaMetadata,
    MediaService,
    MediaUrlType,
)
from kmd.config.logger import get_log_file_stream, get_logger

log = get_logger(__name__)


class LocalFileMedia(MediaService):
    """
    Handle local media files as file:// URLs.
    """

    def _parse_file_url(self, url: Url) -> Optional[Path]:
        parsed_url = urlparse(url)
        if parsed_url.scheme == "file":
            path = Path(parsed_url.path)
            if not path.exists():
                raise FileNotFound(f"File not found: {path}")
            return path
        else:
            return None

    def get_media_id(self, url: Url) -> Optional[str]:
        path = self._parse_file_url(url)
        if path:
            return path.name
        else:
            return None

    def canonicalize_and_type(self, url: Url) -> Tuple[Optional[Url], Optional[MediaUrlType]]:
        path = self._parse_file_url(url)
        if path:
            name, format, file_ext = parse_file_format(path)
            if format.is_audio():
                return url, MediaUrlType.audio
            elif format.is_video():
                return url, MediaUrlType.video
            else:
                raise InvalidInput(f"Unsupported file format: {format}")
        else:
            return None, None

    def thumbnail_url(self, url: Url) -> Optional[Url]:
        return None

    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        return url

    def download_audio(self, url: Url, target_dir: Path) -> Path:
        path = self._parse_file_url(url)
        if not path:
            raise InvalidInput(f"Not a local file URL: {url}")

        _name, format, file_ext = parse_file_format(path)
        if format.is_audio():
            target_path = target_dir / (path.stem + ".mp3")
            os.makedirs(target_dir, exist_ok=True)
            if file_ext == FileExt.mp3:
                log.message(
                    "Copying local audio file: %s -> %s", fmt_path(path), fmt_path(target_dir)
                )
                # If the file is already an MP3 so just copy it.
                copyfile_atomic(path, target_path)
            else:
                log.message(
                    "Converting local audio file: %s -> %s", fmt_path(path), fmt_path(target_dir)
                )
                # Use ffmpeg to convert the audio file to .mp3 format.
                tool_check().require(CmdlineTool.ffmpeg)
                cmdline = ["ffmpeg", "-i", str(path), "-f", "mp3", str(target_path)]
                log.message("Running: %s", " ".join([shlex.quote(arg) for arg in cmdline]))
                subprocess.run(
                    cmdline,
                    check=True,
                    stdout=get_log_file_stream(),
                    stderr=get_log_file_stream(),
                )
            return target_path
        elif format.is_video():
            raise NotImplementedError()  # FIXME: ffmpeg convert
        else:
            raise InvalidInput(f"Unsupported file format: {format}")

    def metadata(self, url: Url, full: bool = False) -> MediaMetadata:
        path = self._parse_file_url(url)
        if not path:
            raise InvalidInput(f"Not a local file URL: {url}")

        name, _format, _file_ext = parse_file_format(path)
        return MediaMetadata(
            title=name,
            url=url,
            media_id=None,
            media_service=None,
        )

    def list_channel_items(self, url: Url) -> List[MediaMetadata]:
        raise NotImplementedError()