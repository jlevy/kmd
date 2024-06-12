from kmd.config.text_styles import NBSP
from kmd.media.video import timestamp_video_url
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


CITE_LEFT_BR = "〔"  # Other options: [〔〘〚〖  ❲⟦⟪⟬

CITE_RIGHT_BR = "〕"


def format_citation(citation: str) -> str:
    return f"""<span class="citation">{CITE_LEFT_BR}{citation}{CITE_RIGHT_BR}</span>"""


def format_timestamp_citation(base_url: Url, timestamp: float) -> str:
    formatted_timestamp = format_timestamp(timestamp)
    timestamp_url = timestamp_video_url(base_url, timestamp)
    return f"""<a href="{timestamp_url}"><span class="citation">{CITE_LEFT_BR}{formatted_timestamp}{CITE_RIGHT_BR}</span></a>"""
