from typing import Tuple

from kmd.exec.action_registry import kmd_action
from kmd.model import Precondition, SequenceAction
from kmd.preconditions.precondition_defs import is_audio_resource, is_url_item, is_video_resource


@kmd_action
class TranscribeAnnotateSummarize(SequenceAction):

    name: str = "transcribe_annotate_summarize"

    description: str = (
        "A fancy action to transcribe a video, format the transcript into paragraphs, backfill timestamps, and add a summary and description."
    )

    action_names: Tuple[str, ...] = (
        "transcribe_format",
        "caption_paras",
        "add_summary_bullets",
        # "add_concepts",  # Better to do this across all docs and review, then reinsert.
        "add_description",
        "insert_frame_captures",
    )

    cacheable: bool = True

    precondition: Precondition = is_url_item | is_audio_resource | is_video_resource

    run_per_item: bool = True
