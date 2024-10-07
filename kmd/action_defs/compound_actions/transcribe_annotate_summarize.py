from kmd.exec.action_registry import kmd_action
from kmd.model import SequenceAction
from kmd.preconditions.precondition_defs import is_audio_resource, is_url, is_video_resource


@kmd_action
class TranscribeAnnotateSummarize(SequenceAction):
    def __init__(self):
        super().__init__(
            name="transcribe_annotate_summarize",
            action_names=[
                "transcribe_format",
                "caption_paras",
                "add_summary_bullets",
                # "add_concepts",  # Better to do this across all docs and review, then reinsert.
                "add_description",
                "insert_frame_captures",
            ],
            description="A fancy action to transcribe a video, format the transcript into paragraphs, backfill timestamps, and add a summary and description.",
            cachable=True,
            precondition=is_url | is_audio_resource | is_video_resource,
            run_per_item=True,
        )
