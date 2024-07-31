import os
from pathlib import Path
from typing import List, Optional
from strif import atomic_output_file
from kmd.config.settings import media_cache_dir
from kmd.model.media_model import MediaMetadata, MediaService
from kmd.model.errors_model import InvalidInput, UnexpectedError
from kmd.util.log_calls import log_calls
from kmd.util.url import Url
from kmd.media.audio import deepgram_transcribe_audio, downsample_to_16khz
from kmd.media.services.youtube import YouTube
from kmd.media.services.vimeo import Vimeo
from kmd.media.services.apple_podcasts import ApplePodcasts
from kmd.util.web_cache import DirStore
from kmd.config.logger import get_logger

log = get_logger(__name__)

# transcribe_audio = whisper_transcribe_audio_small
transcribe_audio = deepgram_transcribe_audio


SUFFIX_16KMP3 = ".16k.mp3"
SUFFIX_MP3 = ".full.mp3"
SUFFIX_TRANSCRIPT = ".transcript.txt"


class MediaCache(DirStore):
    """
    Download and cache video, audio, and transcripts. It's important to cache these by
    default as they are time-consuming and costly to download and process.
    """

    def __init__(self, root):
        super().__init__(root)

    def _write_transcript(self, url: Url, content: str) -> None:
        transcript_path = self.path_for(url, suffix=SUFFIX_TRANSCRIPT)
        with atomic_output_file(transcript_path) as temp_output:
            with open(temp_output, "w") as f:
                f.write(content)
        log.message("Transcript saved to cache: %s", transcript_path)

    def _read_transcript(self, url) -> Optional[str]:
        transcript_file = self.find(url, suffix=SUFFIX_TRANSCRIPT)
        if transcript_file:
            log.message("Video transcript already in cache: %s: %s", url, transcript_file)
            with open(transcript_file, "r") as f:
                return f.read()
        return None

    def _do_downsample(self, url) -> Path:
        downsampled_audio_file = self.find(url, suffix=SUFFIX_16KMP3)
        if not downsampled_audio_file:
            full_audio_file = self.find(url, suffix=SUFFIX_MP3)
            if not full_audio_file:
                raise ValueError("No audio file found for: %s" % url)
            downsampled_audio_file = self.path_for(url, suffix=SUFFIX_16KMP3)
            log.message("Downsampling audio: %s -> %s", full_audio_file, downsampled_audio_file)
            downsample_to_16khz(full_audio_file, downsampled_audio_file)
        return downsampled_audio_file

    def _do_transcription(self, url) -> str:
        downsampled_audio_file = self._do_downsample(url)
        log.message("Transcribing audio: %s: %s", url, downsampled_audio_file)
        transcript = transcribe_audio(downsampled_audio_file)
        self._write_transcript(url, transcript)
        return transcript

    def download(self, url, no_cache=False) -> Path:
        if not no_cache:
            full_audio_file = self.find(url, suffix=SUFFIX_MP3)
            if full_audio_file:
                log.message("Audio already in cache: %s: %s", url, full_audio_file)
                return full_audio_file
        log.message("Downloading audio: %s", url)
        mp3_path = _download_audio_with_service(url)
        full_audio_path = self.path_for(url, suffix=SUFFIX_MP3)
        os.rename(mp3_path, full_audio_path)
        self._do_downsample(url)

        log.message("Downloaded media and saved audio to: %s", full_audio_path)

        return full_audio_path

    def transcribe(self, url, no_cache=False) -> str:
        url = canonicalize_media_url(url)
        if not url:
            raise InvalidInput("Unrecognized media URL: %s" % url)
        if not no_cache:
            transcript = self._read_transcript(url)
            if transcript:
                return transcript
        self.download(url, no_cache=no_cache)
        transcript = self._do_transcription(url)
        if not transcript:
            raise UnexpectedError("No transcript found for: %s" % url)
        return transcript


_media_cache = MediaCache(media_cache_dir())


def _download_audio_with_service(url: Url) -> Path:
    for service in media_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.download_audio(url)
    raise ValueError(f"Unrecognized media URL: {url}")


def download_and_transcribe(url: Url, no_cache=False) -> str:
    """Download and transcribe audio or video, saving in cache. If no_cache is True, force fresh download."""

    return _media_cache.transcribe(url, no_cache=no_cache)


def download_audio(url: Url, no_cache=False) -> Path:
    """Download audio, possibly of a video, saving in cache. If no_cache is True, force fresh download."""

    return _media_cache.download(url, no_cache=no_cache)


# List of available media services.
youtube = YouTube()
vimeo = Vimeo()
apple_podcasts = ApplePodcasts()

media_services: List[MediaService] = [youtube, vimeo, apple_podcasts]


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
