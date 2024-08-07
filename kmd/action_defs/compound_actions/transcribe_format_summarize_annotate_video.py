from kmd.exec.action_combinators import define_action_sequence


define_action_sequence(
    "transcribe_format_summarize_annotate_video",
    [
        "transcribe_format_video",
        "chunk_paragraphs",
        "chunked_summary_bullets",
        "add_description",
    ],
    description="A fancy action to transcribe a video, format the transcript into paragraphs, backfill timestamps, and add a summary and description.",
    on_each_input=True,
)
