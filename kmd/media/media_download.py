from pathlib import Path
from kmd.config.settings import media_cache_dir
from kmd.media.media_cache import MediaCache
from kmd.util.url import Url
from kmd.config.logger import get_logger

log = get_logger(__name__)


_media_cache = MediaCache(media_cache_dir())


def download_and_transcribe(url: Url, no_cache=False) -> str:
    """Download and transcribe audio or video, saving in cache. If no_cache is True, force fresh download."""

    return _media_cache.transcribe(url, no_cache=no_cache)


def download_audio(url: Url, no_cache=False) -> Path:
    """Download audio, possibly of a video, saving in cache. If no_cache is True, force fresh download."""

    return _media_cache.download(url, no_cache=no_cache)
