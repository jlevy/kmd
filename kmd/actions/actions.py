import logging
from kmd.actions.registry import load_all_actions
from kmd.file_storage.file_store import locate_in_store
from kmd.model.actions_model import Action, ActionResult


log = logging.getLogger(__name__)


def run_action(action: str | Action, *args: str) -> ActionResult:
    if not isinstance(action, Action):
        actions = load_all_actions()
        action = actions[action]

    action_name = action.name

    log.warning(f"Running action: %s %s", action_name, " ".join(repr(arg) for arg in args))

    items = [locate_in_store(arg) for arg in args]

    result = action.run(items)
    log.warning(f"Action %s completed with %s items", action_name, len(result))

    return result
