import os
from pathlib import Path
from typing import Dict, Optional

from strif import atomic_output_file

from kmd.config.logger import get_logger
from kmd.errors import FileNotFound, InvalidInput, UnexpectedError
from kmd.media.audio import deepgram_transcribe_audio, downsample_to_16khz
from kmd.media.media_services import canonicalize_media_url, download_media
from kmd.model.media_model import MediaFormat
from kmd.text_formatting.text_formatting import fmt_lines, fmt_path
from kmd.util.url import as_file_url, is_url, Url
from kmd.web_content.web_cache import DirStore

log = get_logger(__name__)

# transcribe_audio = whisper_transcribe_audio_small
transcribe_audio = deepgram_transcribe_audio


# For simplicity we assume all audio is coverted to mp3.
SUFFIX_MP3 = ".full.mp3"
SUFFIX_MP4 = ".full.mp4"
SUFFIX_16KMP3 = ".16k.mp3"
SUFFIX_TRANSCRIPT = ".transcript.txt"


class MediaCache(DirStore):
    """
    Download and cache video, audio, and transcripts. It's important to cache these by
    default as they are time-consuming and costly to download and process. We also
    support local files (as file:// URLs) since we still want to cache downsampled
    audio and transcriptions.
    """

    def __init__(self, root):
        super().__init__(root)

    def _write_transcript(self, url: Url, content: str) -> None:
        transcript_path = self.path_for(url, suffix=SUFFIX_TRANSCRIPT)
        with atomic_output_file(transcript_path) as temp_output:
            with open(temp_output, "w") as f:
                f.write(content)
        log.message("Transcript saved to cache: %s", fmt_path(transcript_path))

    def _read_transcript(self, url: Url) -> Optional[str]:
        transcript_file = self.find(url, suffix=SUFFIX_TRANSCRIPT)
        if transcript_file:
            log.message("Video transcript already in cache: %s: %s", url, fmt_path(transcript_file))
            with open(transcript_file, "r") as f:
                return f.read()
        return None

    def _downsample_audio(self, url: Url) -> Path:
        downsampled_audio_file = self.find(url, suffix=SUFFIX_16KMP3)
        if not downsampled_audio_file:
            full_audio_file = self.find(url, suffix=SUFFIX_MP3)
            if not full_audio_file:
                raise ValueError("No audio file found for: %s" % url)
            downsampled_audio_file = self.path_for(url, suffix=SUFFIX_16KMP3)
            log.message(
                "Downsampling audio: %s -> %s",
                fmt_path(full_audio_file),
                fmt_path(downsampled_audio_file),
            )
            downsample_to_16khz(full_audio_file, downsampled_audio_file)
        return downsampled_audio_file

    def _do_transcription(self, url: Url, language: Optional[str] = None) -> str:
        downsampled_audio_file = self._downsample_audio(url)
        log.message(
            "Transcribing audio: %s: %s",
            url,
            fmt_path(downsampled_audio_file),
        )
        transcript = transcribe_audio(downsampled_audio_file, language=language)
        self._write_transcript(url, transcript)
        return transcript

    def download(self, url: Url, no_cache=False) -> Dict[MediaFormat, Path]:
        cached_paths: Dict[MediaFormat, Path] = {}

        if not no_cache:
            full_audio_file = self.find(url, suffix=SUFFIX_MP3)
            full_video_file = self.find(url, suffix=SUFFIX_MP4)
            if full_audio_file:
                log.message("Audio already in cache: %s: %s", url, fmt_path(full_audio_file))
                cached_paths[MediaFormat.audio_full] = full_audio_file
            if full_video_file:
                log.message("Video already in cache: %s: %s", url, fmt_path(full_video_file))
                cached_paths[MediaFormat.video_full] = full_video_file
            if full_audio_file and full_video_file:
                return cached_paths

        log.message("Downloading media: %s", url)
        media_paths = download_media(url, self.root)
        if MediaFormat.audio_full in media_paths:
            full_audio_path = self.path_for(url, suffix=SUFFIX_MP3)
            os.rename(media_paths[MediaFormat.audio_full], full_audio_path)
            cached_paths[MediaFormat.audio_full] = full_audio_path
        if MediaFormat.video_full in media_paths:
            video_path = self.path_for(url, suffix=SUFFIX_MP4)
            os.rename(media_paths[MediaFormat.video_full], video_path)
            cached_paths[MediaFormat.video_full] = video_path

        log.message(
            "Downloaded media and saved to cache:\n%s",
            fmt_lines([f"{t.name}: {fmt_path(p)}" for (t, p) in cached_paths.items()]),
        )

        self._downsample_audio(url)

        return cached_paths

    def transcribe(
        self, url_or_path: Url | Path, no_cache=False, language: Optional[str] = None
    ) -> str:
        if not isinstance(url_or_path, Path) and is_url(url_or_path):
            url = url_or_path
            url = canonicalize_media_url(url)
            if not url:
                raise InvalidInput("Unrecognized media URL: %s" % url)
            if not no_cache:
                transcript = self._read_transcript(url)
                if transcript:
                    return transcript
            self.download(url, no_cache=no_cache)
        elif isinstance(url_or_path, Path):
            if not url_or_path.exists():
                raise FileNotFound(f"File not found: {fmt_path(url_or_path)}")
            url = as_file_url(url_or_path)
        else:
            raise InvalidInput("Not a media URL or path: %s" % url_or_path)

        transcript = self._do_transcription(url, language=language)
        if not transcript:
            raise UnexpectedError("No transcript found for: %s" % url)
        return transcript
