from kmd.model.compound_actions_model import ComboAction
from kmd.exec.action_registry import kmd_action
from kmd.model.doc_elements import CONCEPTS
from kmd.preconditions.precondition_defs import is_text_doc
from kmd.exec.combiners import combine_as_div_group


@kmd_action(for_each_item=True)
class AddConcepts(ComboAction):
    def __init__(self):
        super().__init__(
            name="add_concepts",
            action_names=["copy_items", "find_concepts"],
            description="Add a brief description of the content above the full text of the item.",
            combiner=combine_as_div_group(CONCEPTS),
            precondition=is_text_doc,
        )
