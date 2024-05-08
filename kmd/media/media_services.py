from abc import ABC, abstractmethod
from typing import Optional

from kmd.util.url_utils import Url


class VideoService(ABC):
    @abstractmethod
    def canonicalize(self, url: Url) -> Optional[Url]:
        """Convert a URL into a canonical form for this service."""
        pass

    @abstractmethod
    def download_audio(self, url: Url) -> str:
        """Download video from URL and extract audio to mp3."""
        pass
