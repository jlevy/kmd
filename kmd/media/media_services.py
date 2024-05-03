from abc import ABC, abstractmethod
from typing import Optional


class VideoService(ABC):
    @abstractmethod
    def canonicalize(self, url: str) -> Optional[str]:
        """Convert a URL into a canonical form for this service."""
        pass

    @abstractmethod
    def download_audio(self, url: str) -> str:
        """Download video from URL and extract audio to mp3."""
        pass
