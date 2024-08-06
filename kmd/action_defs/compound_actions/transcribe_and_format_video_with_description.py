from kmd.exec.action_combinators import define_action_sequence


define_action_sequence(
    "transcribe_and_format_video_with_description",
    [
        "transcribe_and_format_video",
        "chunk_paragraphs",
        "chunked_summary_bullets",
        "add_description",
    ],
    on_each_input=True,
)
