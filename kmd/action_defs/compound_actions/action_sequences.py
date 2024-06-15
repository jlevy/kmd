from kmd.action_exec.action_builders import define_action_sequence


define_action_sequence(
    "transcribe_and_format_video",
    [
        "transcribe_video",
        "strip_html",
        "break_into_paragraphs",
        "backfill_source_timestamps",
    ],
    friendly_name="Transcribe and format video",
    description="Transcribe a video, format the video into paragraphs, and backfill source timestamps on each paragraph.",
)
