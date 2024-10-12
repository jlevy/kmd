from typing import Tuple

from kmd.exec.action_registry import kmd_action
from kmd.exec.combiners import combine_as_div_group, Combiner
from kmd.model import ComboAction, CONCEPTS, Precondition
from kmd.preconditions.precondition_defs import is_text_doc


@kmd_action
class AddConcepts(ComboAction):

    name: str = "add_concepts"

    description: str = "Add a brief description of the content above the full text of the item."

    action_names: Tuple[str, ...] = ("copy_items", "find_concepts")

    combiner: Combiner | None = combine_as_div_group(CONCEPTS)

    precondition: Precondition = is_text_doc

    run_per_item: bool = True
