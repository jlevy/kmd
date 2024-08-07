from kmd.exec.action_combinators import define_action_sequence
from kmd.preconditions.precondition_defs import is_url


define_action_sequence(
    "transcribe_format_video",
    [
        "transcribe",
        "strip_html",
        "break_into_paragraphs",
        "backfill_timestamps",
    ],
    description="Transcribe a video, format the transcript into paragraphs, and backfill source timestamps on each paragraph.",
    on_each_input=True,
    precondition=is_url,
)
