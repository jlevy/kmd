from typing import Tuple

from kmd.exec.action_registry import kmd_action
from kmd.exec.combiners import combine_as_div_group, Combiner
from kmd.model import ComboAction, Precondition, SUMMARY
from kmd.preconditions.precondition_defs import is_text_doc


@kmd_action
class AddSummaryBullets(ComboAction):
    name: str = "add_summary_bullets"

    description: str = (
        "Add a summary of the content as bullet points above the full text of the item."
    )

    action_names: Tuple[str, ...] = ("copy_items", "summarize_as_bullets")

    combiner: Combiner | None = combine_as_div_group(SUMMARY)

    precondition: Precondition = is_text_doc

    run_per_item: bool = True
