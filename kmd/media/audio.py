import logging
from os.path import getsize
from typing import List, NamedTuple, Optional, Tuple
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


class SpeakerSegment(NamedTuple):
    words: List[Tuple[float, str]]
    start: float
    end: float
    speaker: int
    average_confidence: float


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
    log.debug("Diarized response: %s", diarized_segments)

    formatted_segments = format_speaker_segments(diarized_segments)
    return formatted_segments


def _deepgram_diarized_segments(data, confidence_threshold=0.3) -> List[SpeakerSegment]:
    """Process Deepgram diarized results into text segments per speaker."""

    speaker_segments = []
    current_speaker = 0
    current_text = []
    current_confidences = []
    segment_start = 0.0
    segment_end = 0.0

    word_info_list = data["results"]["channels"][0]["alternatives"][0]["words"]

    for word_info in word_info_list:
        word_confidence = word_info["confidence"]
        word_speaker = word_info["speaker"]
        word_start = float(word_info["start"])
        word_end = float(word_info["end"])
        punctuated_word = word_info["punctuated_word"]

        previous_confidence = current_confidences[-1] if current_confidences else 0
        confidence_dropped = word_confidence < confidence_threshold * previous_confidence
        if confidence_dropped:
            log.debug(
                "Speaker confidence dropped from %s to %s for '%s'",
                previous_confidence,
                word_confidence,
                punctuated_word,
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
                    words=current_text,
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
        current_text.append((word_start, punctuated_word))
        current_confidences.append(word_confidence)
        segment_end = word_end

    # Append the last speaker's segment.
    if current_text and current_confidences:
        average_confidence = sum(current_confidences) / len(current_confidences)
        speaker_segments.append(
            SpeakerSegment(
                words=current_text,
                start=segment_start,
                end=segment_end,
                speaker=current_speaker,
                average_confidence=average_confidence,
            )
        )

    return speaker_segments


def _is_new_sentence(word: str, next_word: Optional[str]) -> bool:
    return (
        (word.endswith(".") or word.endswith("?") or word.endswith("!"))
        and next_word is not None
        and next_word[0].isupper()
    )


def _format_words(words: List[Tuple[float, str]], include_sentence_timestamps=True) -> str:
    """Format words with timestamps added in spans."""

    if not words:
        return ""

    sentences = []
    current_sentence = []
    for i, (timestamp, word) in enumerate(words):
        current_sentence.append(word)
        next_word = words[i + 1][1] if i + 1 < len(words) else None
        if _is_new_sentence(word, next_word):
            sentences.append((timestamp, current_sentence))
            current_sentence = []

    if current_sentence:
        sentences.append((words[-1][0], current_sentence))

    formatted_text = []
    for timestamp, sentence in sentences:
        formatted_sentence = " ".join(sentence)
        if include_sentence_timestamps:
            formatted_text.append(
                f'<span data-timestamp="{timestamp:.2f}">{formatted_sentence}</span>'
            )
        else:
            formatted_text.append(formatted_sentence)

    return "\n".join(formatted_text)


def format_speaker_segments(speaker_segments: List[SpeakerSegment]) -> str:
    """Format speaker segments for display."""

    speakers = set(segment.speaker for segment in speaker_segments)
    if len(speakers) > 1:
        lines = []
        for segment in speaker_segments:
            lines.append(f"**SPEAKER {segment.speaker}:**\n{_format_words(segment.words)}")
        return "\n\n".join(lines)
    else:
        return "\n\n".join(_format_words(segment.words) for segment in speaker_segments)
