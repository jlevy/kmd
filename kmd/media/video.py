import logging
import os
from typing import Optional
from strif import atomic_output_file
from kmd.config import MEDIA_CACHE_DIR
from .audio import deepgram_transcribe_audio, downsample_to_16khz
from ..util.web_cache import DirStore
from .video_youtube import YouTube
from .video_vimeo import Vimeo

log = logging.getLogger(__name__)


# transcribe_audio = whisper_transcribe_audio_small
transcribe_audio = deepgram_transcribe_audio


class VideoCache(DirStore):
    """Download and cache video, audio, and transcripts from videos."""

    def __init__(self, root):
        super().__init__(root)

    def _write_transcript(self, url: str, content: str) -> None:
        with atomic_output_file(self.path_for(url, suffix=".txt")) as temp_output:
            with open(temp_output, "w") as f:
                f.write(content)

    def _read_transcript(self, url) -> Optional[str]:
        transcript_file = self.find(url, suffix=".txt")
        if transcript_file:
            log.info("Video transcript in cache: %s: %s", url, transcript_file)
            with open(transcript_file, "r") as f:
                return f.read()
        return None

    def _do_downsample(self, url):
        downsampled_audio_file = self.find(url, suffix=".16k.mp3")
        if not downsampled_audio_file:
            full_audio_file = self.find(url, suffix=".mp3")
            if not full_audio_file:
                raise ValueError("No audio file found for: %s" % url)
            downsampled_audio_file = self.path_for(url, suffix=".16k.mp3")
            log.info(
                "Downsampling YouTube audio: %s -> %s",
                full_audio_file,
                downsampled_audio_file,
            )
            downsample_to_16khz(full_audio_file, downsampled_audio_file)
        return downsampled_audio_file

    def _do_transcription(self, url):
        downsampled_audio_file = self._do_downsample(url)
        log.info("Transcribing audio for video: %s -> %s", url, downsampled_audio_file)
        transcript = transcribe_audio(downsampled_audio_file)
        self._write_transcript(url, transcript)
        return transcript

    def download(self, url, no_cache=False) -> str:
        if not no_cache:
            full_audio_file = self.find(url, suffix=".mp3")
            if full_audio_file:
                log.info("Audio of video in cache: %s: %s", url, full_audio_file)
                return full_audio_file
        log.info("Downloading audio of video: %s", url)
        mp3_path = download_video_mp3(url)
        full_audio_file = self.path_for(url, suffix=".mp3")
        os.rename(mp3_path, full_audio_file)
        self._do_downsample(url)
        return full_audio_file

    def transcribe(self, url, no_cache=False) -> str:
        url = canonicalize_video_url(url)
        if not url:
            raise ValueError("Unrecognized video URL: %s" % url)
        if not no_cache:
            transcript = self._read_transcript(url)
            if transcript:
                return transcript
        self.download(url, no_cache=no_cache)
        transcript = self._do_transcription(url)
        if transcript:
            return transcript
        else:
            raise ValueError("No transcript found for: %s" % url)


_video_cache = VideoCache(MEDIA_CACHE_DIR)


def video_transcription(url: str, no_cache=False) -> str:
    """Transcribe a YouTube video. If no_cache is True, force fresh download."""

    return _video_cache.transcribe(url, no_cache=no_cache)


# List of available video services.
video_services = [YouTube(), Vimeo()]


def video_download(url: str) -> str:
    """Download video from a supported service (like YouTube)."""

    for service in video_services:
        if service.canonicalize(url):
            return service.download_audio(url)
    raise ValueError(f"Unrecognized video URL: {url}")


def canonicalize_video_url(url: str) -> Optional[str]:
    """Return the canonical form of a video URL from a supported service (like YouTube)."""

    for service in video_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return canonical_url
    return None


def download_video_mp3(url: str) -> str:
    """Download the audio component of a video as an MP3."""

    for service in video_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.download_audio(url)
    raise ValueError(f"Unrecognized video URL: {url}")
