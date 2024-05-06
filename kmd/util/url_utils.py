import logging
from urllib.parse import urlsplit, urlunsplit

log = logging.getLogger(__name__)


def normalize_url(url):
    """
    Minimal URL normalization. Removes fragment.
    """
    scheme, netloc, path, query, fragment = urlsplit(url)
    normalized_url = urlunsplit((scheme, netloc, path, query, None))
    if url != normalized_url:
        log.info("Normalized URL: %s -> %s" % (url, normalized_url))
    return normalized_url
