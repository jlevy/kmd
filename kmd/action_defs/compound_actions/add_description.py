from kmd.exec.action_registry import kmd_action
from kmd.exec.combiners import combine_as_div_group
from kmd.model import ComboAction, DESCRIPTION
from kmd.preconditions.precondition_defs import is_text_doc


@kmd_action
class AddDescription(ComboAction):
    def __init__(self):
        super().__init__(
            name="add_description",
            action_names=["copy_items", "describe_briefly"],
            description="Add a brief description of the content above the full text of the item.",
            combiner=combine_as_div_group(DESCRIPTION),
            precondition=is_text_doc,
            run_per_item=True,
        )
