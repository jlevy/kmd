import os
from pathlib import Path
from typing import Optional
from strif import atomic_output_file
from kmd.media.media_services import canonicalize_media_url, media_services
from kmd.model.errors_model import InvalidInput, UnexpectedError
from kmd.util.url import Url
from kmd.media.audio import deepgram_transcribe_audio, downsample_to_16khz
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


def _download_audio_with_service(url: Url) -> Path:
    for service in media_services:
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.download_audio(url)
    raise ValueError(f"Unrecognized media URL: {url}")
