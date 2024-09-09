from typing import List, Optional

from kmd.config.logger import get_logger
from kmd.media.services.apple_podcasts import ApplePodcasts
from kmd.media.services.local_file_media import LocalFileMedia
from kmd.media.services.vimeo import Vimeo
from kmd.media.services.youtube import YouTube
from kmd.model.errors_model import InvalidInput
from kmd.model.media_model import MediaMetadata, MediaService
from kmd.util.log_calls import log_calls
from kmd.util.url import Url

log = get_logger(__name__)


# List of available media services.
local_file_media = LocalFileMedia()
youtube = YouTube()
vimeo = Vimeo()
apple_podcasts = ApplePodcasts()

media_services: List[MediaService] = [local_file_media, youtube, vimeo, apple_podcasts]


def canonicalize_media_url(url: Url) -> Optional[Url]:
    """
    Return the canonical form of a media URL from a supported service (like YouTube).
    """
    for service in media_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return canonical_url
    return None


def thumbnail_media_url(url: Url) -> Optional[Url]:
    """
    Return a URL that links to the thumbnail of the media.
    """
    for service in media_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.thumbnail_url(url)
    return None


def timestamp_media_url(url: Url, timestamp: float) -> Url:
    """
    Return a URL that links to the media at the given timestamp.
    """
    for service in media_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.timestamp_url(url, timestamp)
    raise InvalidInput(f"Unrecognized media URL: {url}")


def get_media_id(url: Url | None) -> Optional[str]:
    if not url:
        return None
    for service in media_services:
        media_id = service.get_media_id(url)
        if media_id:
            return media_id
    return None


@log_calls(level="info", show_return=True)
def get_media_metadata(url: Url) -> Optional[MediaMetadata]:
    """
    Return metadata for the media at the given URL.
    """
    for service in media_services:
        media_id = service.get_media_id(url)
        if media_id:  # This is an actual video, not a channel etc.
            return service.metadata(url)
    return None


def list_channel_items(url: Url) -> List[MediaMetadata]:
    """
    List all items in a channel.
    """
    for service in media_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.list_channel_items(url)
    raise InvalidInput(f"Unrecognized media URL: {url}")
