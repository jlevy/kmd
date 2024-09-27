from kmd.exec.action_registry import kmd_action
from kmd.exec.combiners import combine_as_div_group
from kmd.model import ComboAction, SUMMARY
from kmd.preconditions.precondition_defs import is_text_doc


@kmd_action
class AddSummaryBullets(ComboAction):
    def __init__(self):
        super().__init__(
            name="add_summary_bullets",
            action_names=["copy_items", "summarize_as_bullets"],
            description="Add a summary of the content as bullet points above the full text of the item.",
            combiner=combine_as_div_group(SUMMARY),
            precondition=is_text_doc,
            run_per_item=True,
        )
