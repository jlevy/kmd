from kmd.config.text_styles import NBSP
from kmd.media.media_services import timestamp_media_url
from kmd.model.doc_elements import CITATION
from kmd.util.url import Url
from kmd.text_formatting.html_in_md import html_span, html_a


def add_citation_to_text(text: str, citation: str) -> str:
    return f"{text}{NBSP}{citation}"


def format_timestamp(timestamp: float) -> str:
    hours, remainder = divmod(timestamp, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    else:
        return f"{int(minutes):02}:{int(seconds):02}"


CITE_LEFT_BR = "⟦"

CITE_RIGHT_BR = "⟧"

# More bracket options:
# [❲⟦⟪⟬〔〘〚〖
# ]❳⟧⟫⟭ 〕〙〛〗


def format_citation(citation: str, safe: bool = False) -> str:
    return html_span(f"{CITE_LEFT_BR}{citation}{CITE_RIGHT_BR}", CITATION, safe=safe)


def add_citation_to_sentence(old_sent: str, source_url: Url | None, timestamp: float) -> str:
    return add_citation_to_text(old_sent, format_timestamp_citation(source_url, timestamp))


def format_timestamp_citation(base_url: Url | None, timestamp: float) -> str:
    formatted_timestamp = format_timestamp(timestamp)
    if base_url:
        timestamp_url = timestamp_media_url(base_url, timestamp)
        link = html_a(formatted_timestamp, timestamp_url)
        citation = format_citation(link, safe=True)
    else:
        citation = format_citation(f"{formatted_timestamp}")
    return citation
