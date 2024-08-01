from pathlib import Path
from kmd.config.settings import get_settings
from kmd.media.media_cache import MediaCache
from kmd.util.url import Url
from kmd.config.logger import get_logger

log = get_logger(__name__)


_media_cache = MediaCache(get_settings().media_cache_dir)


def reset_media_cache_dir(path: Path):
    get_settings().media_cache_dir = path
    global _media_cache
    _media_cache = MediaCache(path)
    log.info("Using media cache: %s", path)


def download_and_transcribe(url: Url, no_cache=False) -> str:
    """Download and transcribe audio or video, saving in cache. If no_cache is True, force fresh download."""

    return _media_cache.transcribe(url, no_cache=no_cache)


def download_audio(url: Url, no_cache=False) -> Path:
    """Download audio, possibly of a video, saving in cache. If no_cache is True, force fresh download."""

    return _media_cache.download(url, no_cache=no_cache)
