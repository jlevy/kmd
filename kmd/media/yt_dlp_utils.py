import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Dict

import yt_dlp

from kmd.config.logger import get_logger
from kmd.file_formats.yaml_util import to_yaml_string
from kmd.model.errors_model import ApiResultError
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


def ydl_download_audio(url: Url, target_dir: Path | None = None) -> Path:
    """
    Download and convert to mp3 using yt_dlp, which is generally the best library for this.
    """

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
        "logger": log,
    }

    log.info("Extracting audio from media %s at %s", url, temp_dir)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        audio_file_path = ydl.prepare_filename(info_dict)

    # yt_dlp returns the .webm file, so this is the converted .mp3.
    mp3_path = os.path.splitext(audio_file_path)[0] + ".mp3"
    return Path(mp3_path)
