from kmd.action_exec.action_combinators import define_action_sequence


define_action_sequence(
    "transcribe_and_format_video",
    [
        "transcribe_video",
        "strip_html",
        "break_into_paragraphs",
        "backfill_source_timestamps",
    ],
    description="Transcribe a video, format the transcript into paragraphs, and backfill source timestamps on each paragraph.",
    on_each_input=True,
)
