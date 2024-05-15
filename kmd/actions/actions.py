import logging
from kmd.actions.registry import load_all_actions
from kmd.file_storage.file_store import current_workspace, ensure_saved
from kmd.model.actions_model import Action, ActionResult
from kmd.model.locators import StorePath
from kmd.util.type_utils import assert_not_none

from strif import abbreviate_list

log = logging.getLogger(__name__)


def run_action(action: str | Action, *args: str) -> ActionResult:
    if not isinstance(action, Action):
        actions = load_all_actions()
        action = actions[action]

    action_name = action.name

    log.warning(f"Running action: %s %s", action_name, " ".join(repr(arg) for arg in args))

    items = [ensure_saved(arg) for arg in args]

    result = action.run(items)
    log.warning(f"Action %s completed with %s items", action_name, len(result))

    store_paths = [StorePath(assert_not_none(item.store_path)) for item in result]

    current_workspace().set_selection(store_paths)

    log.warning(f"Selected %s items: %s", len(store_paths), abbreviate_list(store_paths))

    return result
