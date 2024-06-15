from kmd.action_exec.action_builders import define_action_combo, define_action_sequence


define_action_sequence(
    "transcribe_and_format_video",
    [
        "transcribe_video",
        "strip_html",
        "break_into_paragraphs",
        "backfill_source_timestamps",
    ],
    friendly_name="Get a formatted video transcript, with timestamps",
    description="Transcribe a video, format the video into paragraphs, and backfill source timestamps on each paragraph.",
)

define_action_combo(
    "add_description",
    ["brief_description", "copy_items"],
    friendly_name="Add a Description",
    description="Add a brief summary at the top of the item.",
)


define_action_sequence(
    "transcribe_and_format_video_with_description",
    [
        "transcribe_and_format_video",
        "add_description",
    ],
)
