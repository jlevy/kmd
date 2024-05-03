import logging
import os
import tempfile
from typing import Optional
from urllib.parse import urlparse, parse_qs
from pydub import AudioSegment
import yt_dlp
from vimeo_downloader import Vimeo
from strif import atomic_output_file

from kmd.config import MEDIA_CACHE_DIR
from .audio import deepgram_transcribe_audio, downsample_to_16khz, whisper_transcribe_audio_small
from ..util.web_cache import DirStore

log = logging.getLogger(__name__)


# transcribe_audio = whisper_transcribe_audio_small
transcribe_audio = deepgram_transcribe_audio


class VideoCache(DirStore):
    """Download and cache audio from YouTube or Vimeo videos and transcripts."""

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


def video_download(url: str) -> str:
    """"""
    return _video_cache.download(url)


def canonical_youtube_url(url):
    parsed_url = urlparse(url)

    if parsed_url.hostname == "youtu.be":
        video_id = parsed_url.path[1:]
    elif parsed_url.hostname in ("www.youtube.com", "youtube.com"):
        query = parse_qs(parsed_url.query)
        video_id = query.get("v", [""])[0]
    else:
        return None
    if not video_id:
        return None

    return f"https://www.youtube.com/watch?v={video_id}"


def youtube_download_audio(url: str, target_dir: Optional[str] = None) -> str:
    """Download and convert to mp3. yt_dlp seems like the best library for this."""

    temp_dir = target_dir or tempfile.mkdtemp()
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(temp_dir, "audio.%(id)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        audio_file_path = ydl.prepare_filename(info_dict)

    # yt_dlp returns the .webm file, so this is the converted .mp3.
    mp3_path = os.path.splitext(audio_file_path)[0] + ".mp3"
    return mp3_path


def canonical_vimeo_url(url):
    parsed_url = urlparse(url)

    if parsed_url.hostname == "vimeo.com":
        video_id = parsed_url.path[1:]
    else:
        return None
    if not video_id:
        return None

    return f"https://vimeo.com/{video_id}"


def vimeo_download_audio(url: str) -> str:
    """Download and convert to mp3."""

    temp_dir = tempfile.mkdtemp()

    v = Vimeo(url)
    stream = v.streams[0]  # Pick the worst.
    video_path = stream.download(download_directory=temp_dir, filename="video.mp4", mute=True)

    mp3_path = os.path.join(temp_dir, "extracted_audio.mp3")
    log.info("Extracting audio from Vimeo video %s at %s to %s", url, video_path, mp3_path)
    audio = AudioSegment.from_file(video_path, format="mp4")
    audio.export(mp3_path, format="mp3")

    return mp3_path


def canonicalize_video_url(url: str):
    return canonical_youtube_url(url) or canonical_vimeo_url(url)


def download_video_mp3(url: str):
    youtube_url = canonical_youtube_url(url)
    if youtube_url:
        return youtube_download_audio(url)

    vimeo_url = canonical_vimeo_url(url)
    if vimeo_url:
        return vimeo_download_audio(vimeo_url)

    raise ValueError("Unrecognized video URL: %s" % url)
