import os
from pathlib import Path
from typing import List, Optional
from strif import atomic_output_file
from kmd.config.settings import media_cache_dir
from kmd.model.media_model import MediaMetadata, MediaService
from kmd.model.errors_model import InvalidInput, UnexpectedError
from kmd.util.url import Url
from kmd.media.audio import deepgram_transcribe_audio, downsample_to_16khz
from kmd.media.video_youtube import YouTube
from kmd.media.video_vimeo import Vimeo
from kmd.util.web_cache import DirStore
from kmd.config.logger import get_logger

log = get_logger(__name__)

# transcribe_audio = whisper_transcribe_audio_small
transcribe_audio = deepgram_transcribe_audio


SUFFIX_16KMP3 = ".16k.mp3"
SUFFIX_MP3 = ".full.mp3"
SUFFIX_TRANSCRIPT = ".transcript.txt"


class VideoCache(DirStore):
    """
    Download and cache video, audio, and transcripts from videos.
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
            log.message(
                "Downsampling YouTube audio: %s -> %s", full_audio_file, downsampled_audio_file
            )
            downsample_to_16khz(full_audio_file, downsampled_audio_file)
        return downsampled_audio_file

    def _do_transcription(self, url) -> str:
        downsampled_audio_file = self._do_downsample(url)
        log.message("Transcribing audio for video: %s: %s", url, downsampled_audio_file)
        transcript = transcribe_audio(downsampled_audio_file)
        self._write_transcript(url, transcript)
        return transcript

    def download(self, url, no_cache=False) -> Path:
        if not no_cache:
            full_audio_file = self.find(url, suffix=SUFFIX_MP3)
            if full_audio_file:
                log.message("Audio of video already in cache: %s: %s", url, full_audio_file)
                return full_audio_file
        log.message("Downloading audio of video: %s", url)
        mp3_path = _download_audio_with_service(url)
        full_audio_path = self.path_for(url, suffix=SUFFIX_MP3)
        os.rename(mp3_path, full_audio_path)
        self._do_downsample(url)

        log.message("Downloaded video and saved audio to: %s", full_audio_path)

        return full_audio_path

    def transcribe(self, url, no_cache=False) -> str:
        url = canonicalize_video_url(url)
        if not url:
            raise InvalidInput("Unrecognized video URL: %s" % url)
        if not no_cache:
            transcript = self._read_transcript(url)
            if transcript:
                return transcript
        self.download(url, no_cache=no_cache)
        transcript = self._do_transcription(url)
        if not transcript:
            raise UnexpectedError("No transcript found for: %s" % url)
        return transcript


_video_cache = VideoCache(media_cache_dir())


def _download_audio_with_service(url: Url) -> Path:
    for service in video_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.download_audio(url)
    raise ValueError(f"Unrecognized video URL: {url}")


def video_transcription(url: Url, no_cache=False) -> str:
    """Transcribe a video, saving in cache. If no_cache is True, force fresh download."""

    return _video_cache.transcribe(url, no_cache=no_cache)


def video_download_audio(url: Url, no_cache=False) -> Path:
    """Download audio of a video, saving in cache. If no_cache is True, force fresh download."""

    return _video_cache.download(url, no_cache=no_cache)


# List of available video services.
youtube = YouTube()
vimeo = Vimeo()
video_services: List[MediaService] = [youtube, vimeo]


def canonicalize_video_url(url: Url) -> Optional[Url]:
    """
    Return the canonical form of a video URL from a supported service (like YouTube).
    """
    for service in video_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return canonical_url
    return None


def thumbnail_video_url(url: Url) -> Optional[Url]:
    """
    Return a URL that links to the thumbnail of the video.
    """
    for service in video_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.thumbnail_url(url)
    return None


def timestamp_video_url(url: Url, timestamp: float) -> Url:
    """
    Return a URL that links to the video at the given timestamp.
    """
    for service in video_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.timestamp_url(url, timestamp)
    raise InvalidInput(f"Unrecognized video URL: {url}")


def get_video_id(url: Url | None) -> Optional[str]:
    """
    Extract the video ID from a URL.
    """
    if not url:
        return None
    for service in video_services:
        video_id = service.get_id(url)
        if video_id:
            return video_id
    return None


def get_video_metadata(url: Url) -> Optional[MediaMetadata]:
    """
    Return metadata for the video at the given URL.
    """
    for service in video_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.metadata(url)
    return None
