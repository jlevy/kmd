from kmd.media.video import canonicalize_video_url
from kmd.model.locators import Url
from kmd.util.url_utils import normalize_url


def canonicalize_url(url: Url) -> Url:
    """
    Canonicalize a URL for known services, otherwise do basic normalization on the URL.
    """

    return canonicalize_video_url(url) or normalize_url(url)
