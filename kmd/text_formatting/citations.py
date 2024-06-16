from kmd.config.text_styles import NBSP
from kmd.media.video import timestamp_video_url
from kmd.util.url import Url
from kmd.text_formatting.html_in_md import CITATION, html_span, html_a


def add_citation_to_text(text: str, citation: str) -> str:
    return f"{text}{NBSP}{citation}"


def format_timestamp(timestamp: float) -> str:
    hours, remainder = divmod(timestamp, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    else:
        return f"{int(minutes):02}:{int(seconds):02}"


CITE_LEFT_BR = "〔"  # Other options: [〔〘〚〖  ❲⟦⟪⟬

CITE_RIGHT_BR = "〕"


def format_citation(citation: str) -> str:
    return html_span(f"{CITE_LEFT_BR}{citation}{CITE_RIGHT_BR}", CITATION)


def format_timestamp_citation(base_url: Url, timestamp: float) -> str:
    formatted_timestamp = format_timestamp(timestamp)
    citation = format_citation(formatted_timestamp)
    timestamp_url = timestamp_video_url(base_url, timestamp)
    return html_a(citation, timestamp_url)
