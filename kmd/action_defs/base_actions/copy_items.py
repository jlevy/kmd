from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import Item, PerItemAction

log = get_logger(__name__)


@kmd_action
class CopyAction(PerItemAction):
    def __init__(self):
        super().__init__(
            name="copy_items",
            description="Identity action that copies the input items with no changes. Useful in combo actions.",
            cachable=False,
        )

    def run_item(self, item: Item) -> Item:
        return item
