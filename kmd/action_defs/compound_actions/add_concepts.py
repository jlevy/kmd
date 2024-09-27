from kmd.exec.action_registry import kmd_action
from kmd.exec.combiners import combine_as_div_group
from kmd.model import ComboAction, CONCEPTS
from kmd.preconditions.precondition_defs import is_text_doc


@kmd_action
class AddConcepts(ComboAction):
    def __init__(self):
        super().__init__(
            name="add_concepts",
            action_names=["copy_items", "find_concepts"],
            description="Add a brief description of the content above the full text of the item.",
            combiner=combine_as_div_group(CONCEPTS),
            precondition=is_text_doc,
            run_per_item=True,
        )
