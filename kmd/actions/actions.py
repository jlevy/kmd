import logging
from typing import List, cast
from strif import abbreviate_str
from kmd.actions.registry import load_all_actions
from kmd.file_storage.file_store import NoSelectionError
from kmd.file_storage.workspaces import current_workspace, ensure_saved
from kmd.model.actions_model import Action, ActionResult
from kmd.model.locators import StorePath
from kmd.util.text_formatting import format_lines
from kmd.util.type_utils import not_none
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

    log.warning(
        f"Running action: %s %s",
        action_name,
        abbreviate_str(" ".join(repr(arg) for arg in args), max_len=200),
    )

    # Ensure any items that are not saved are already in the workspace and get the corresponding items.
    # This looks up any URLs.
    input_items = [ensure_saved(arg) for arg in args]

    result = action.run(input_items)
    log.warning(f"Action %s completed with %s items", action_name, len(result.items))

    result_store_paths = [StorePath(not_none(item.store_path)) for item in result.items]
    current_workspace().set_selection(result_store_paths)

    # If there is a hint that the action replaces the input, archive any inputs that are not in the result.
    if result.replaces_input and input_items:
        for item in input_items:
            input_store_path = StorePath(not_none(item.store_path))
            if input_store_path not in result_store_paths:
                current_workspace().archive(input_store_path)
                log.warning("Archived input item: %s", input_store_path)

    commands.select()

    return result
