from typing import Iterable, List

from kmd.config.logger import get_logger

from kmd.errors import SkippableError
from kmd.file_storage.file_store import FileStore
from kmd.model.actions_model import Action
from kmd.model.items_model import Item
from kmd.model.paths_model import StorePath
from kmd.model.preconditions_model import Precondition
from kmd.text_formatting.text_formatting import fmt_path

log = get_logger(__name__)


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
        try:
            item = ws.load(store_path)
        except SkippableError:
            continue
        except Exception as e:
            log.info("Ignoring exception loading item %s: %s", fmt_path(store_path), e)
            continue
        if precondition(item):
            yield item
            count += 1
