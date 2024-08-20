from kmd.exec.action_combinators import define_action_sequence
from kmd.preconditions.precondition_defs import is_url


define_action_sequence(
    "transcribe_format_summarize_annotate_video",
    [
        "transcribe_format_video",
        "chunkify",
        "find_concepts_chunked",
        "summarize_as_bullets_chunked",
        "add_description",
    ],
    description="A fancy action to transcribe a video, format the transcript into paragraphs, backfill timestamps, and add a summary and description.",
    on_each_input=True,
    precondition=is_url,
)
