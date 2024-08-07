from kmd.exec.action_combinators import combine_with_divs, define_action_combo
from kmd.model.html_conventions import DESCRIPTION, FULL_TEXT
from kmd.preconditions.precondition_defs import is_readable_text


define_action_combo(
    "add_description",
    ["describe_briefly", "copy_items"],
    description="Add a brief description of the content above the full text of the item.",
    combiner=combine_with_divs(DESCRIPTION, FULL_TEXT),
    on_each_input=True,
    precondition=is_readable_text,
)
