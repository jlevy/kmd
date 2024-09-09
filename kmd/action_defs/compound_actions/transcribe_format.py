from kmd.exec.action_registry import kmd_action
from kmd.preconditions.precondition_defs import is_url
from kmd.model import CachedDocSequence


@kmd_action(for_each_item=True)
class TranscribeFormat(CachedDocSequence):
    def __init__(self):
        super().__init__(
            name="transcribe_format",
            action_names=[
                "transcribe",
                "strip_html",
                "break_into_paragraphs",
                "backfill_timestamps",
            ],
            description="Transcribe a video, format the transcript into paragraphs, and backfill source timestamps on each paragraph.",
            precondition=is_url,
        )
