from pathlib import Path
from typing import Dict, List, Optional

from kmd.config.logger import get_logger
from kmd.config.settings import global_settings, update_global_settings
from kmd.media.media_cache import MediaCache
from kmd.model.media_model import MediaType
from kmd.util.format_utils import fmt_path
from kmd.util.url import Url

log = get_logger(__name__)


_media_cache = MediaCache(global_settings().media_cache_dir)


def reset_media_cache_dir(path: Path):
    """
    Reset the current media cache directory, if it has changed.
    """
    with update_global_settings() as settings:
        current_cache_dir = settings.media_cache_dir

        if current_cache_dir != path:
            settings.media_cache_dir = path
            global _media_cache
            _media_cache = MediaCache(path)
            log.info("Using media cache: %s", fmt_path(path))


def cache_and_transcribe(
    url_or_path: Url | Path, no_cache=False, language: Optional[str] = None
) -> str:
    """
    Download and transcribe audio or video, saving in cache. If no_cache is
    True, force fresh download.
    """
    return _media_cache.transcribe(url_or_path, no_cache=no_cache, language=language)


def cache_media(
    url: Url, no_cache=False, media_types: Optional[List[MediaType]] = None
) -> Dict[MediaType, Path]:
    """
    Download audio and video (if available), saving in cache. If no_cache is
    True, force fresh download.
    """
    return _media_cache.cache(url, no_cache, media_types)
