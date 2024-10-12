from typing import Tuple

from kmd.exec.action_registry import kmd_action
from kmd.model import Precondition, SequenceAction
from kmd.preconditions.precondition_defs import is_audio_resource, is_url, is_video_resource


@kmd_action
class TranscribeFormat(SequenceAction):

    name: str = "transcribe_format"

    description: str = (
        "Transcribe a video, format the transcript into paragraphs, and backfill source timestamps on each paragraph."
    )

    action_names: Tuple[str, ...] = (
        "transcribe",
        "identify_speakers",
        "strip_html",
        "break_into_paragraphs",
        "backfill_timestamps",
        "insert_section_headings",
    )

    cachable: bool = True

    precondition: Precondition = is_url | is_audio_resource | is_video_resource

    run_per_item: bool = True
