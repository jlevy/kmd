import logging
from urllib.parse import urlsplit, urlunsplit

log = logging.getLogger(__name__)


def normalize_url(url: str, expect_http=True, remove_fragment=True) -> str:
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
    return normalized_url
