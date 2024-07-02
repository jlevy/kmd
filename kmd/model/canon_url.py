from typing import Optional
from kmd.media.video import canonicalize_video_url, thumbnail_video_url
from kmd.util.url import Url, normalize_url


def canonicalize_url(url: Url) -> Url:
    """
    Canonicalize a URL for known services, otherwise do basic normalization on the URL.
    """
    return canonicalize_video_url(url) or normalize_url(url)


def thumbnail_url(url: Url) -> Optional[Url]:
    """
    Return a URL for a thumbnail of the given URL, if available.
    """
    # Currently just for videos. Consider adding support for images and webpages.
    return thumbnail_video_url(url)
