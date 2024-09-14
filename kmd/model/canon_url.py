from typing import Optional

from kmd.media.media_services import canonicalize_media_url, thumbnail_media_url
from kmd.util.log_calls import log_if_modifies
from kmd.util.url import normalize_url, Url

_normalize_url = log_if_modifies(level="info")(normalize_url)


def canonicalize_url(url: Url) -> Url:
    """
    Canonicalize a URL for known services, otherwise do basic normalization on the URL.
    """
    return canonicalize_media_url(url) or _normalize_url(url)


def thumbnail_url(url: Url) -> Optional[Url]:
    """
    Return a URL for a thumbnail of the given URL, if available.
    """
    # Currently just for videos. Consider adding support for images and webpages.
    return thumbnail_media_url(url)
