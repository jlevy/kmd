from kmd.model import ComboAction
from kmd.exec.action_registry import kmd_action
from kmd.model import DESCRIPTION
from kmd.preconditions.precondition_defs import is_text_doc
from kmd.exec.combiners import combine_as_div_group


@kmd_action(for_each_item=True)
class AddDescription(ComboAction):
    def __init__(self):
        super().__init__(
            name="add_description",
            action_names=["copy_items", "describe_briefly"],
            description="Add a brief description of the content above the full text of the item.",
            combiner=combine_as_div_group(DESCRIPTION),
            precondition=is_text_doc,
        )
