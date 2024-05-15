import logging
from typing import List, cast
from kmd.actions.registry import load_all_actions
from kmd.file_storage.file_store import NoSelectionError, current_workspace, ensure_saved
from kmd.model.actions_model import Action, ActionResult
from kmd.model.locators import StorePath
from kmd.util.text_formatting import format_lines
from kmd.util.type_utils import assert_not_none
from kmd.commands import commands

log = logging.getLogger(__name__)


def collect_args(*args: str) -> List[str]:
    if not args:
        try:
            selection_args = current_workspace().get_selection()
            return cast(List[str], selection_args)
        except NoSelectionError:
            return []
    else:
        return list(args)


def run_action(action: str | Action, *provided_args: str) -> ActionResult:

    # Get the action and action name.
    if not isinstance(action, Action):
        actions = load_all_actions()
        action = actions[action]
    action_name = action.name

    # Collect args from the provided args or otherwise the current selection.
    args = collect_args(*provided_args)
    if provided_args:
        log.warning(f"Using provided args:\n%s", format_lines(provided_args))
    elif args:
        log.warning(f"Using selection:\n%s", format_lines(args))

    # Ensure we have the right number of args.
    action.validate_args(args)

    log.warning(f"Running action: %s %s", action_name, " ".join(repr(arg) for arg in args))

    # Ensure any items that are not saved are already in the workspace and get the corresponding items.
    # This looks up any URLs.
    items = [ensure_saved(arg) for arg in args]

    result = action.run(items)
    log.warning(f"Action %s completed with %s items", action_name, len(result))

    store_paths = [StorePath(assert_not_none(item.store_path)) for item in result]

    current_workspace().set_selection(store_paths)

    commands.selection()

    return result
