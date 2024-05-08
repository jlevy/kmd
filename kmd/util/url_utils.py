import logging
from typing import NewType
from urllib.parse import urlsplit, urlunsplit

log = logging.getLogger(__name__)

Url = NewType("Url", str)


def is_url(text: str) -> bool:
    """
    Check if a string is a URL.
    """

    return text.startswith("http://") or text.startswith("https://")


def normalize_url(url: Url, expect_http=True, remove_fragment=True) -> Url:
    """
    Minimal URL normalization. By default also enforces http/https and removes fragment.
    """

    # urlsplit is too forgiving.
    if expect_http and not url.startswith("http://") and not url.startswith("https://"):
        raise ValueError(f"Expected http/https URL but found: {url}")

    scheme, netloc, path, query, fragment = urlsplit(url)

    if remove_fragment:
        fragment = None
    normalized_url = urlunsplit((scheme, netloc, path, query, fragment))
    if url != normalized_url:
        log.info("Normalized URL: %s -> %s" % (url, normalized_url))
    return Url(normalized_url)
