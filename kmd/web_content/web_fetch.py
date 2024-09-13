import enum
import re
from pathlib import Path

import requests

from kmd.config.logger import get_logger
from kmd.config.settings import global_settings, update_global_settings
from kmd.errors import WebFetchError
from kmd.text_formatting.text_formatting import fmt_path
from kmd.util.url import Url
from kmd.web_content.web_cache import WebCache

log = get_logger(__name__)


class ContentType(enum.Enum):
    markdown = "markdown"
    html = "html"
    text = "text"


def guess_text_content_type(content: str) -> ContentType:
    """
    Simple best-effort guess at content type.
    """

    if re.search(r"<html>|<body>|<head>|<div>|<p>", content, re.IGNORECASE | re.MULTILINE):
        return ContentType.html

    if re.search(r"^#+ |^- |\*\*|__", content, re.MULTILINE):
        return ContentType.markdown

    return ContentType.text


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
            global _web_cache
            _web_cache = WebCache(path)
            log.info("Using web cache: %s", fmt_path(path))


def fetch_and_cache(url: Url) -> Path:
    """
    Fetch the given URL and return a local cached copy. Raises requests.HTTPError
    if the URL is not reachable.
    """
    path, _was_cached = _web_cache.fetch(url)
    return path
