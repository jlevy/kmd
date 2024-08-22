from kmd.exec.action_registry import kmd_action
from kmd.preconditions.precondition_defs import is_url
from kmd.exec.compound_actions import SequenceAction


@kmd_action(for_each_item=True)
class TranscribeAnnotateSummarize(SequenceAction):
    def __init__(self):
        super().__init__(
            name="transcribe_annotate_summarize",
            action_names=[
                "transcribe_and_format",
                "caption_paras",
                "chunkify",
                "summarize_as_bullets_chunked",
                "add_concepts",
                "add_description",
            ],
            description="A fancy action to transcribe a video, format the transcript into paragraphs, backfill timestamps, and add a summary and description.",
            precondition=is_url,
        )
