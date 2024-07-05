from kmd.action_exec.action_combinators import define_action_sequence


define_action_sequence(
    "transcribe_and_format_video_with_description",
    [
        "transcribe_and_format_video",
        "add_description",
    ],
    on_each_input=True,
)
