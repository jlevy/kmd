from typing import Iterable, List
from kmd.file_storage.file_store import FileStore
from kmd.model.actions_model import Action
from kmd.model.locators import StorePath
from kmd.model.items_model import Item
from kmd.model.preconditions_model import Precondition


def actions_matching_paths(
    actions: Iterable[Action],
    ws: FileStore,
    paths: List[StorePath],
    include_no_precondition: bool = False,
) -> Iterable[Action]:
    """
    Which actions satisfy the preconditions for all the given paths.
    """

    def check_precondition(action: Action, store_path: StorePath) -> bool:
        if action.precondition:
            return action.precondition(ws.load(store_path))
        else:
            return include_no_precondition

    for action in actions:
        if all(check_precondition(action, store_path) for store_path in paths):
            yield action


def items_matching_precondition(
    ws: FileStore, precondition: Precondition, max_results: int = 0
) -> Iterable[Item]:
    """
    Yield items matching the given precondition, up to max_results if specified.
    """
    count = 0
    for store_path in ws.walk_items():
        if max_results > 0 and count >= max_results:
            break
        item = ws.load(store_path)
        if precondition(item):
            yield item
            count += 1