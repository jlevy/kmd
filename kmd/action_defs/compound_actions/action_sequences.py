from kmd.action_exec.action_combinators import (
    combine_with_divs,
    define_action_combo,
    define_action_sequence,
)
from kmd.text_formatting.html_in_md import DESCRIPTION, FULL_TEXT


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
    combiner=combine_with_divs(DESCRIPTION, FULL_TEXT),
)


define_action_sequence(
    "transcribe_and_format_video_with_description",
    [
        "transcribe_and_format_video",
        "add_description",
    ],
)
