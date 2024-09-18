from pathlib import Path
from typing import Dict

import requests

from kmd.config.logger import get_logger
from kmd.config.settings import global_settings, update_global_settings
from kmd.errors import FileNotFound, WebFetchError
from kmd.media.media_services import is_media_url
from kmd.media.media_tools import cache_media
from kmd.model.file_formats_model import detect_media_type
from kmd.model.items_model import Item
from kmd.model.media_model import MediaType
from kmd.preconditions.precondition_defs import is_resource
from kmd.util.format_utils import fmt_lines, fmt_path
from kmd.util.url import Url
from kmd.web_content.web_cache import WebCache

log = get_logger(__name__)


USER_AGENT = "Mozilla/5.0"


def fetch(url: Url) -> requests.Response:
    response = requests.get(url, headers={"User-Agent": USER_AGENT})
    log.info("Fetched: %s (%s bytes): %s", response.status_code, len(response.content), url)
    if response.status_code != 200:
        raise WebFetchError(f"HTTP error {response.status_code} fetching {url}")
    return response


# Simple global cache for misc use. No expiration.
_web_cache = WebCache(global_settings().web_cache_dir)


def reset_web_cache_dir(path: Path):
    with update_global_settings() as settings:
        current_cache_dir = settings.web_cache_dir
        if current_cache_dir != path:
            settings.web_cache_dir = path
            log.info("Using web cache: %s", fmt_path(path))

    global _web_cache
    _web_cache = WebCache(global_settings().web_cache_dir)


def cache(url_or_path: Url | Path) -> tuple[Path, bool]:
    """
    Fetch the given URL and return a local cached copy. Raises requests.HTTPError
    if the URL is not reachable. If a local file path is given, it is cached
    (using a file:// URL as the key).
    """
    path, was_cached = _web_cache.cache(url_or_path)
    return path, was_cached


def cache_resource(item: Item) -> Dict[MediaType, Path]:
    """
    Cache a resource item for an external local path or a URL, fetching or
    copying as needed. For media this may yield more than one format.
    """
    if not is_resource(item):
        raise ValueError(f"Item is not a resource: {item}")

    if item.url:
        if is_media_url(item.url):
            result = cache_media(item.url)
        else:
            path, _was_cached = cache(item.url)
    elif item.external_path:
        path = Path(item.external_path)
        if not path.is_file():
            raise FileNotFound(f"External path not found: {path}")
        path, _was_cached = cache(path)
    else:
        raise ValueError("Item has no URL or external path")

    # If we just have the local file path, determine its format.
    if not result and path:
        result = {detect_media_type(path): path}

    log.message(
        "Cached copy of item %s:\n%s",
        item.as_str_brief(),
        fmt_lines(
            f"{media_type.value}: {fmt_path(media_path)}"
            for media_type, media_path in result.items()
        ),
    )

    return result
