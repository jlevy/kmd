from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional
from kmd.util.url import Url


@dataclass
class HeatmapValue:
    """
    A value in a heatmap. Matches YouTube's format.
    """

    start_time: int
    end_time: int
    value: float


@dataclass
class MediaMetadata:
    """
    Metadata for an audio or video file from a service like YouTube, Vimeo, etc.
    """

    title: str
    description: Optional[str] = None
    url: Optional[Url] = None
    thumbnail_url: Optional[Url] = None

    id: Optional[str] = None
    upload_date: Optional[date] = None
    channel_url: Optional[Url] = None
    view_count: Optional[int] = None
    duration: Optional[int] = None
    heatmap: Optional[List[HeatmapValue]] = None


class MediaService(ABC):
    """
    An audio or video service like YouTube, Vimeo, Spotify, etc.
    """

    @abstractmethod
    def canonicalize(self, url: Url) -> Optional[Url]:
        """Convert a URL into a canonical form for this service."""
        pass

    @abstractmethod
    def get_id(self, url: Url) -> str:
        """Extract the media ID from a URL."""
        pass

    @abstractmethod
    def metadata(self, url: Url) -> MediaMetadata:
        """Return metadata for the media at the given URL."""
        pass

    @abstractmethod
    def thumbnail_url(self, url: Url) -> Optional[Url]:
        """Return a URL that links to the thumbnail of the media."""
        pass

    @abstractmethod
    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        """Return a URL that links to the media at the given timestamp."""
        pass

    @abstractmethod
    def download_audio(self, url: Url) -> Path:
        """Download media from URL and extract audio to mp3."""
        pass
