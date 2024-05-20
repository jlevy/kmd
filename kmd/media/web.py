import enum
import re
from typing import Optional
from cachetools import TTLCache, cached
from strif import abbreviate_str
import requests
import justext

from kmd.media.video import canonicalize_video_url
from kmd.util.url_utils import Url
from kmd.config.logging import get_logger

log = get_logger(__name__)


class CrawlError(ValueError):
    pass


class PageType(enum.Enum):
    html = 1
    pdf = 2
    video = 3

    def as_str(self) -> str:
        return self.name

    # TODO: Use mimetime as well.
    @classmethod
    def from_url(cls, url: Url) -> "PageType":
        if canonicalize_video_url(url):
            return cls.video
        if url.endswith(".pdf"):
            return cls.pdf
        return cls.html


class PageData:
    """
    Data about a page, including URL, title and optionally description and extracted content.
    """

    def __init__(
        self,
        url: Url,
        type: PageType = PageType.html,
        title: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
    ) -> None:
        self.url = url
        self.type = type
        self.title = title
        self.description = description
        self.content = content

    def __repr__(self) -> str:
        return f"PageData(url={self.url!r}, type={self.type!r} title={self.title!r}, description={abbreviate_str(self.description)!r}, content={abbreviate_str(self.content)!r})"


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
        raise CrawlError(f"HTTP error {response.status_code} fetching {url}")
    return response


@cached(cache=TTLCache(maxsize=100, ttl=600))
def fetch_extract(url: Url) -> PageData:
    """
    Fetches a URL and extracts the title, description, and content.
    """

    # TODO: Consider a JS-enabled headless browser so it works on more sites.
    # Example: https://www.inc.com/atish-davda/5-questions-you-should-ask-before-taking-a-start-up-job-offer.html
    # TODO: Use the DirCache to save raw HTML content in disk cache.
    response = fetch(url)
    return _extract_page_data_from_html(url, response.content)


def _extract_page_data_from_html(url: Url, raw_html: bytes) -> PageData:
    dom, paragraphs = _justext_custom(raw_html, justext.get_stoplist("English"))
    # Extract title and description.
    title = None
    description = None
    try:
        title = str(dom.cssselect("title")[0].text_content())
    except IndexError:
        pass
    try:
        description = str(dom.cssselect('meta[name="description"]')[0].get("content"))
    except IndexError:
        pass

    # Content without boilerplate.
    content = "\n\n".join([para.text for para in paragraphs if not para.is_boilerplate])
    return PageData(url, PageType.from_url(url), title, description, content)


from justext.core import (
    LENGTH_LOW_DEFAULT,
    LENGTH_HIGH_DEFAULT,
    STOPWORDS_LOW_DEFAULT,
    STOPWORDS_HIGH_DEFAULT,
    MAX_LINK_DENSITY_DEFAULT,
    MAX_HEADING_DISTANCE_DEFAULT,
    NO_HEADINGS_DEFAULT,
    DEFAULT_ENCODING,
    DEFAULT_ENC_ERRORS,
    preprocessor,
    html_to_dom,
    ParagraphMaker,
    classify_paragraphs,
    revise_paragraph_classification,
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
