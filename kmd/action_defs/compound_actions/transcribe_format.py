from kmd.exec.action_registry import kmd_action
from kmd.model import SequenceAction
from kmd.preconditions.precondition_defs import is_audio_resource, is_url, is_video_resource


@kmd_action
class TranscribeFormat(SequenceAction):
    def __init__(self):
        super().__init__(
            name="transcribe_format",
            action_names=[
                "transcribe",
                "identify_speakers",
                "strip_html",
                "break_into_paragraphs",
                "backfill_timestamps",
            ],
            description="Transcribe a video, format the transcript into paragraphs, and backfill source timestamps on each paragraph.",
            cachable=True,
            precondition=is_url | is_audio_resource | is_video_resource,
            run_per_item=True,
        )
