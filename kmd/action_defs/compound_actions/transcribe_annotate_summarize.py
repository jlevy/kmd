from kmd.exec.action_registry import kmd_action
from kmd.model import CachedDocSequence
from kmd.preconditions.precondition_defs import is_url


@kmd_action(for_each_item=True)
class TranscribeAnnotateSummarize(CachedDocSequence):
    def __init__(self):
        super().__init__(
            name="transcribe_annotate_summarize",
            action_names=[
                "transcribe_format",
                "caption_paras",
                "add_concepts",
                "add_summary_bullets",
                "add_description",
            ],
            description="A fancy action to transcribe a video, format the transcript into paragraphs, backfill timestamps, and add a summary and description.",
            precondition=is_url,
        )
