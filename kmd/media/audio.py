import logging
from collections import namedtuple
from os.path import getsize
from typing import List
from openai import OpenAI
from deepgram import DeepgramClient, PrerecordedOptions, FileSource, ClientOptionsFromEnv
from pydub import AudioSegment
from strif import atomic_output_file

from kmd import config


log = logging.getLogger(__name__)


def downsample_to_16khz(audio_file_path: str, downsampled_out_path: str) -> None:
    audio = AudioSegment.from_mp3(audio_file_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    with atomic_output_file(downsampled_out_path) as temp_target:
        audio.export(temp_target, format="mp3")

    log.info(
        "Downsampled %s -> %s: size %s to 16kHz size %s (%sX reduction)",
        audio_file_path,
        downsampled_out_path,
        getsize(audio_file_path),
        getsize(downsampled_out_path),
        getsize(audio_file_path) / getsize(downsampled_out_path),
    )


# Max as of 2024-05 is 25MB.
# https://help.openai.com/en/articles/7031512-whisper-api-faq
WHISPER_MAX_SIZE = 25 * 1024 * 1024


def whisper_transcribe_audio_small(audio_file_path: str) -> str:
    """Transcribe an audio file. Must be under 25MB."""
    size = getsize(audio_file_path)
    if size > WHISPER_MAX_SIZE:
        raise ValueError("Audio file too large for Whisper (%s > %s)" % (size, WHISPER_MAX_SIZE))
    log.info(
        "Transcribing via Whisper: %s (size %s)",
        audio_file_path,
        size,
    )

    client = OpenAI()
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            # For when we want timestamps:
            # response_format="verbose_json",
            # timestamp_granularities=["word"]
        )
        text = transcription.text
    return text


SpeakerSegment = namedtuple(
    "SpeakerSegment", ["speaker_text", "start", "end", "speaker", "average_confidence"]
)


def deepgram_transcribe_audio(audio_file_path: str) -> str:
    """Transcribe an audio file using Deepgram."""

    size = getsize(audio_file_path)
    log.info("Transcribing via Deepgram: %s (size %s)", audio_file_path, size)

    config.api_setup()
    deepgram = DeepgramClient("", ClientOptionsFromEnv())

    with open(audio_file_path, "rb") as audio_file:
        buffer_data = audio_file.read()

    payload: FileSource = {
        "buffer": buffer_data,
    }

    options = PrerecordedOptions(model="nova-2", smart_format=True, diarize=True)
    response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options, timeout=600)

    diarized_segments = _deepgram_diarized_segments(response)
    log.info("Diarized response: %s", diarized_segments)

    formatted_segments = format_speaker_segments(diarized_segments)
    return formatted_segments


def _deepgram_diarized_segments(data, confidence_threshold=0.3) -> List[SpeakerSegment]:
    """Process Deepgram diarized results into text segments per speaker."""

    speaker_segments = []
    current_speaker = None
    current_text = []
    current_confidences = []
    segment_start = None
    segment_end = None

    for word_info in data["results"]["channels"][0]["alternatives"][0]["words"]:
        word_confidence = word_info["confidence"]
        word_speaker = word_info["speaker"]
        word_start = word_info["start"]
        word_end = word_info["end"]

        previous_confidence = current_confidences[-1] if current_confidences else 0
        confidence_dropped = word_confidence < confidence_threshold * previous_confidence
        if confidence_dropped:
            log.debug(
                "Speaker confidence dropped from %s to %s for '%s'",
                previous_confidence,
                word_confidence,
                word_info["punctuated_word"],
            )

        # Start a new segment at the start, when the speaker changes, or when confidence drops significantly.
        if current_speaker is None:
            # Initialize for the very first word.
            current_speaker = word_speaker
            segment_start = word_start
        elif current_speaker != word_speaker or confidence_dropped:
            average_confidence = (
                sum(current_confidences) / len(current_confidences) if current_confidences else 0
            )
            speaker_segments.append(
                SpeakerSegment(
                    speaker_text=" ".join(current_text),
                    start=segment_start,
                    end=segment_end,
                    speaker=current_speaker,
                    average_confidence=average_confidence,
                )
            )
            # Reset for new speaker segment.
            current_text = []
            current_confidences = []
            current_speaker = word_speaker
            segment_start = word_start

        # Append current word to the segment.
        current_text.append(word_info["punctuated_word"])
        current_confidences.append(word_confidence)
        segment_end = word_end

    # Append the last speaker's segment.
    if current_text and current_confidences:
        average_confidence = sum(current_confidences) / len(current_confidences)
        speaker_segments.append(
            SpeakerSegment(
                speaker_text=" ".join(current_text),
                start=segment_start,
                end=segment_end,
                speaker=current_speaker,
                average_confidence=average_confidence,
            )
        )

    return speaker_segments


def format_speaker_segments(speaker_segments: List[SpeakerSegment]) -> str:
    """Format speaker segments for display."""

    lines = []
    for segment in speaker_segments:
        lines.append(f"SPEAKER {segment.speaker}:\n{segment.speaker_text}")
    return "\n\n".join(lines)
