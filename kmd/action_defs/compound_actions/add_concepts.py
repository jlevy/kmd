from kmd.exec.compound_actions import ComboAction
from kmd.exec.action_registry import kmd_action
from kmd.model.doc_elements import CONCEPTS, FULL_TEXT
from kmd.preconditions.precondition_defs import is_readable_text
from kmd.exec.combiners import combine_with_divs


@kmd_action(for_each_item=True)
class AddConcepts(ComboAction):
    def __init__(self):
        super().__init__(
            name="add_concepts",
            action_names=["find_concepts", "copy_items"],
            description="Add a brief description of the content above the full text of the item.",
            combiner=combine_with_divs(CONCEPTS, FULL_TEXT),
            precondition=is_readable_text,
        )
