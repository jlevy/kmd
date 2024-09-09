from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import ANY_ARGS, ForEachItemAction, Item

log = get_logger(__name__)


@kmd_action()
class CopyAction(ForEachItemAction):
    def __init__(self):
        super().__init__(
            name="copy_items",
            description="Identity action that copies the input items with no changes. Useful in combo actions.",
            expected_args=ANY_ARGS,
        )

    def run_item(self, item: Item) -> Item:
        return item
