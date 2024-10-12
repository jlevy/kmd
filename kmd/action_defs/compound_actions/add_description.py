from typing import Tuple

from kmd.exec.action_registry import kmd_action
from kmd.exec.combiners import combine_as_div_group, Combiner
from kmd.model import ComboAction, DESCRIPTION, Precondition
from kmd.preconditions.precondition_defs import is_text_doc


@kmd_action
class AddDescription(ComboAction):

    name: str = "add_description"

    description: str = "Add a brief description of the content above the full text of the item."

    action_names: Tuple[str, ...] = ("copy_items", "describe_briefly")

    combiner: Combiner | None = combine_as_div_group(DESCRIPTION)

    precondition: Precondition = is_text_doc

    run_per_item: bool = True
