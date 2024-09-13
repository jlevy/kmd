import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Dict

import yt_dlp

from kmd.config.logger import get_logger
from kmd.errors import ApiResultError
from kmd.file_formats.yaml_util import to_yaml_string
from kmd.model.media_model import MediaFormat
from kmd.util.url import Url


log = get_logger(__name__)


def parse_date(upload_date: str | date) -> date:
    if isinstance(upload_date, str):
        return date.fromisoformat(upload_date)
    elif isinstance(upload_date, date):
        return upload_date
    raise ValueError(f"Invalid date: {upload_date}")


def ydl_extract_info(url: Url) -> Dict[str, Any]:
    ydl_opts = {
        "extract_flat": "in_playlist",  # Extract metadata only, without downloading.
        "quiet": True,
        "dump_single_json": True,
        "logger": log,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(str(url), download=False)

        log.save_object("yt_dlp result", None, to_yaml_string(result, stringify_unknown=True))

        if not isinstance(result, dict):
            raise ApiResultError(f"Unexpected result from yt_dlp: {result}")

        return result


def ydl_download_media(
    url: Url, target_dir: Path | None = None, include_video: bool = False
) -> Dict[MediaFormat, Path]:
    """
    Download and convert to mp3 and mp4 using yt_dlp, which is generally the best library for this.
    """

    temp_dir = target_dir or tempfile.mkdtemp()
    if include_video:
        ydl_opts = {
            # Try for best video+audio, fall back to best available.
            # This outputs both video and audio (even with just the one postprocessor).
            # Might want to support smaller sizes tho.
            "format": "bestvideo+bestaudio/best",
            # "format": "bestvideo[height<=720]+bestaudio/best",
            "outtmpl": os.path.join(temp_dir, "media.%(id)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                },
            ],
        }
    else:
        ydl_opts = {
            # Try for best video+audio, fall back to best available.
            "format": "bestaudio/best",
            "outtmpl": os.path.join(temp_dir, "media.%(id)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                },
            ],
        }

    # Use our logger.
    ydl_opts["logger"] = log

    log.info("Extracting media from %s at %s using ydl_opts: %s", url, temp_dir, ydl_opts)

    info_dict = None
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        media_file_path = ydl.prepare_filename(info_dict)

    result_paths = {}

    log.info("ydl output filename: %s", media_file_path)

    # Check if the audio file exists.
    mp3_path = os.path.splitext(media_file_path)[0] + ".mp3"
    if os.path.exists(mp3_path):
        result_paths[MediaFormat.audio_full] = Path(mp3_path)
    else:
        log.warn("mp3 download not found: %s", mp3_path)

    if include_video:
        # Check if video file exists.
        mp4_path = os.path.splitext(media_file_path)[0] + ".mp4"
        if os.path.exists(mp4_path):
            result_paths[MediaFormat.video_full] = Path(mp4_path)
        else:
            log.warn("mp4 download not found: %s", mp4_path)

    return result_paths
