from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import Item, PerItemAction

log = get_logger(__name__)


@kmd_action
@dataclass
class CopyItems(PerItemAction):

    name: str = "copy_items"

    description: str = """
        Identity action that copies the input items with no changes. Useful in combo actions.
        """

    cacheable: bool = False

    def run_item(self, item: Item) -> Item:
        return item
