import enum
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import justext
import requests

from kmd.config.logger import get_logger
from kmd.config.settings import global_settings, update_global_settings
from kmd.media.media_services import canonicalize_media_url
from kmd.model.canon_url import thumbnail_url
from kmd.model.errors_model import WebFetchError
from kmd.text_formatting.text_formatting import fmt_path
from kmd.util.log_calls import log_calls
from kmd.util.obj_utils import abbreviate_obj
from kmd.util.url import Url
from kmd.util.web_cache import WebCache

log = get_logger(__name__)


class PageType(enum.Enum):
    html = "html"
    pdf = "pdf"
    video = "video"

    def as_str(self) -> str:
        return self.name

    # TODO: Use mimetime as well.
    @classmethod
    def from_url(cls, url: Url) -> "PageType":
        if canonicalize_media_url(url):
            return cls.video
        if url.endswith(".pdf"):
            return cls.pdf
        return cls.html


@dataclass
class PageData:
    """
    Data about a page, including URL, title and optionally description and extracted content.
    """

    url: Url
    type: PageType = PageType.html
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    thumbnail_url: Optional[Url] = None

    def __str__(self):
        return abbreviate_obj(self)


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


@log_calls(level="message")
def fetch_extract(url: Url, cache=True) -> PageData:
    """
    Fetches a URL and extracts the title, description, and content.
    """

    # TODO: Consider a JS-enabled headless browser so it works on more sites.
    # Example: https://www.inc.com/atish-davda/5-questions-you-should-ask-before-taking-a-start-up-job-offer.html

    if cache:
        path = fetch_and_cache(url)
        with open(path, "rb") as file:
            content = file.read()
        page_data = _extract_page_data_from_html(url, content)
    else:
        response = fetch(url)
        page_data = _extract_page_data_from_html(url, response.content)

    # Add a thumbnail, if available.
    page_data.thumbnail_url = thumbnail_url(url)

    return page_data


def _extract_page_data_from_html(url: Url, raw_html: bytes) -> PageData:
    dom, paragraphs = _justext_custom(raw_html, justext.get_stoplist("English"))
    # Extract title and description.
    title = None
    description = None
    try:
        title = str(dom.cssselect("title")[0].text_content()).strip()
    except IndexError:
        log.warning("Page missing title: %s", url)
        log.save_object("Page missing title", "web", raw_html)
        pass
    try:
        description = str(dom.cssselect('meta[name="description"]')[0].get("content"))
    except IndexError:
        pass

    # Content without boilerplate.
    content = "\n\n".join([para.text for para in paragraphs if not para.is_boilerplate])
    return PageData(
        url, PageType.from_url(url), title=title, description=description, content=content
    )


from justext.core import (
    classify_paragraphs,
    DEFAULT_ENC_ERRORS,
    DEFAULT_ENCODING,
    html_to_dom,
    LENGTH_HIGH_DEFAULT,
    LENGTH_LOW_DEFAULT,
    MAX_HEADING_DISTANCE_DEFAULT,
    MAX_LINK_DENSITY_DEFAULT,
    NO_HEADINGS_DEFAULT,
    ParagraphMaker,
    preprocessor,
    revise_paragraph_classification,
    STOPWORDS_HIGH_DEFAULT,
    STOPWORDS_LOW_DEFAULT,
)


# Copied from justext to expose the dom and save time parsing.
def _justext_custom(
    html_text,
    stoplist,
    length_low=LENGTH_LOW_DEFAULT,
    length_high=LENGTH_HIGH_DEFAULT,
    stopwords_low=STOPWORDS_LOW_DEFAULT,
    stopwords_high=STOPWORDS_HIGH_DEFAULT,
    max_link_density=MAX_LINK_DENSITY_DEFAULT,
    max_heading_distance=MAX_HEADING_DISTANCE_DEFAULT,
    no_headings=NO_HEADINGS_DEFAULT,
    encoding=None,
    default_encoding=DEFAULT_ENCODING,
    enc_errors=DEFAULT_ENC_ERRORS,
    preprocessor=preprocessor,
):
    """
    Converts an HTML page into a list of classified paragraphs. Each paragraph
    is represented as instance of class ˙˙justext.paragraph.Paragraph˙˙.
    """
    dom = html_to_dom(html_text, default_encoding, encoding, enc_errors)
    clean_dom = preprocessor(dom)

    paragraphs = ParagraphMaker.make_paragraphs(clean_dom)

    classify_paragraphs(
        paragraphs,
        stoplist,
        length_low,
        length_high,
        stopwords_low,
        stopwords_high,
        max_link_density,
        no_headings,
    )
    revise_paragraph_classification(paragraphs, max_heading_distance)

    return dom, paragraphs


if __name__ == "__main__":
    sample_urls = [
        "https://hbr.org/2016/12/think-strategically-about-your-career-development",
        "https://www.chicagobooth.edu/review/how-answer-one-toughest-interview-questions",
        "https://www.inc.com/atish-davda/5-questions-you-should-ask-before-taking-a-start-up-job-offer.html",
        "https://www.investopedia.com/terms/r/risktolerance.asp",
        "https://www.upcounsel.com/employee-offer-letter",
        "https://rework.withgoogle.com/guides/pay-equity/steps/introduction/",
        "https://www.forbes.com/sites/tanyatarr/2017/12/31/here-are-five-negotiation-myths-we-can-leave-behind-in-2017/",
        "https://archive.nytimes.com/dealbook.nytimes.com/2009/08/19/googles-ipo-5-years-later/",
    ]

    for url in sample_urls:
        print(f"URL: {url}")
        print(fetch_extract(Url(url)))
        print()
