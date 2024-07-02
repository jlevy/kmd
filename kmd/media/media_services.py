from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from kmd.util.url import Url


class VideoService(ABC):
    @abstractmethod
    def canonicalize(self, url: Url) -> Optional[Url]:
        """Convert a URL into a canonical form for this service."""
        pass

    @abstractmethod
    def get_id(self, url: Url) -> str:
        """Extract the video ID from a URL."""
        pass

    @abstractmethod
    def thumbnail_url(self, url: Url) -> Optional[Url]:
        """Return a URL that links to the thumbnail of the video."""
        pass

    @abstractmethod
    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        """Return a URL that links to the video at the given timestamp."""
        pass

    @abstractmethod
    def download_audio(self, url: Url) -> Path:
        """Download video from URL and extract audio to mp3."""
        pass
