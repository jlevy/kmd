from pathlib import Path
from typing import Optional
from kmd.config.settings import global_settings, update_global_settings
from kmd.media.media_cache import MediaCache
from kmd.text_formatting.text_formatting import fmt_path
from kmd.util.url import Url
from kmd.config.logger import get_logger

log = get_logger(__name__)


_media_cache = MediaCache(global_settings().media_cache_dir)


def reset_media_cache_dir(path: Path):
    with update_global_settings() as settings:
        current_cache_dir = settings.media_cache_dir
        if current_cache_dir != path:
            settings.media_cache_dir = path
            global _media_cache
            _media_cache = MediaCache(path)
            log.info("Using media cache: %s", fmt_path(path))


def download_and_transcribe(url: Url, no_cache=False, language: Optional[str] = None) -> str:
    """Download and transcribe audio or video, saving in cache. If no_cache is True, force fresh download."""

    return _media_cache.transcribe(url, no_cache=no_cache, language=language)


def download_audio(url: Url, no_cache=False) -> Path:
    """Download audio, possibly of a video, saving in cache. If no_cache is True, force fresh download."""

    return _media_cache.download(url, no_cache=no_cache)
