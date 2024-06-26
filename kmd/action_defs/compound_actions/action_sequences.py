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
    description="Transcribe a video, format the transcript into paragraphs, and backfill source timestamps on each paragraph.",
    on_each_input=True,
)

define_action_combo(
    "add_description",
    ["describe_briefly", "copy_items"],
    description="Add a brief description of the content above the full text of the item.",
    combiner=combine_with_divs(DESCRIPTION, FULL_TEXT),
    on_each_input=True,
)


define_action_sequence(
    "transcribe_and_format_video_with_description",
    [
        "transcribe_and_format_video",
        "add_description",
    ],
    on_each_input=True,
)
