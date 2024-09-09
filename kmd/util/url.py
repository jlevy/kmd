from pathlib import Path
from typing import NewType, Optional
from urllib.parse import urlparse, urlsplit, urlunsplit

from kmd.config.logger import get_logger


log = get_logger(__name__)

Url = NewType("Url", str)
"""
A minimal URL type that functions like a string but allows for better clarity
and type checking.
"""


def is_url(text: str, http_only: bool = False) -> bool:
    """
    Check if a string is a URL.
    """
    try:
        result = urlparse(text)
        if http_only:
            return result.scheme in ["http", "https"]
        else:
            return result.scheme != ""
    except ValueError:
        return False


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


def as_file_url(path: Path) -> Url:
    return Url(f"file://{path.resolve()}")


def parse_file_url(url: Url) -> Optional[Path]:
    parsed_url = urlparse(url)
    if parsed_url.scheme == "file":
        return Path(parsed_url.path)
    else:
        return None


## Tests


def test_is_url():
    assert is_url("http://") == True
    assert is_url("http://example.com") == True
    assert is_url("https://example.com") == True
    assert is_url("ftp://example.com") == True
    assert is_url("file:///path/to/file") == True
    assert is_url("file://hostname/path/to/file") == True
    assert is_url("invalid-url") == False
    assert is_url("www.example.com") == False
    assert is_url("http://example.com", http_only=True) == True
    assert is_url("https://example.com", http_only=True) == True
    assert is_url("ftp://example.com", http_only=True) == False
    assert is_url("file:///path/to/file", http_only=True) == False
