from kmd.config.text_styles import NBSP
from kmd.media.media_services import timestamp_media_url
from kmd.model.doc_elements import CITATION, DATA_SOURCE_PATH, DATA_TIMESTAMP, TIMESTAMP_LINK
from kmd.text_formatting.html_in_md import html_a, html_span
from kmd.util.url import Url


def add_citation_to_text(text: str, citation: str) -> str:
    return f"{text}{NBSP}{citation}"


def format_timestamp(timestamp: float) -> str:
    hours, remainder = divmod(timestamp, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    else:
        return f"{int(minutes):02}:{int(seconds):02}"


def format_citation(citation: str) -> str:
    return html_span(f"{citation}", CITATION, safe=True)


def add_citation_to_sentence(
    old_sent: str, source_url: Url | None, source_path: str, timestamp: float
) -> str:
    return add_citation_to_text(
        old_sent, format_timestamp_citation(source_url, source_path, timestamp)
    )


def format_timestamp_citation(
    base_url: Url | None, source_path: str, timestamp: float, emoji: str = "⏱️"
) -> str:
    formatted_timestamp = format_timestamp(timestamp)
    if base_url:
        timestamp_url = timestamp_media_url(base_url, timestamp)
        formatted_timestamp = html_a(formatted_timestamp, timestamp_url)

    return html_span(
        f"{emoji}{formatted_timestamp}&nbsp;",
        [CITATION, TIMESTAMP_LINK],
        attrs={DATA_SOURCE_PATH: source_path, DATA_TIMESTAMP: f"{timestamp:.2f}"},
        safe=True,
    )
