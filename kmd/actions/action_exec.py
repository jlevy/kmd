from typing import List, cast
from strif import abbreviate_str
from kmd.actions.action_registry import load_all_actions
from kmd.file_storage.file_store import NoSelectionError
from kmd.file_storage.workspaces import current_workspace, ensure_saved
from kmd.model.actions_model import Action, ActionResult
from kmd.model.locators import StorePath
from kmd.text_formats.text_formatting import format_lines
from kmd.util.type_utils import not_none
from kmd.commands import commands
from kmd.config.logger import get_logger

log = get_logger(__name__)


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
        log.message(f"Using provided args:\n%s", format_lines(provided_args))
    elif args:
        log.message(f"Using selection:\n%s", format_lines(args))

    # Ensure we have the right number of args.
    action.validate_args(args)

    log.message(
        f"Running action: %s %s",
        action_name,
        abbreviate_str(" ".join(repr(arg) for arg in args), max_len=200),
    )

    # Ensure any items that are not saved are already in the workspace and get the corresponding items.
    # This looks up any URLs.
    input_items = [ensure_saved(arg) for arg in args]

    # Run the action.
    result = action.run(input_items)

    # TODO: Consider moving save here, instead of always doing it within the action.
    for item in result.items:
        if not item.store_path:
            raise ValueError(f"Result Item should have a store path (forgot to save?): {item}")

    log.message(f"Action %s completed with %s items", action_name, len(result.items))

    input_store_paths = [StorePath(not_none(item.store_path)) for item in input_items]
    result_store_paths = [StorePath(not_none(item.store_path)) for item in result.items]
    old_inputs = sorted(set(input_store_paths) - set(result_store_paths))
    new_outputs = sorted(set(result_store_paths) - set(input_store_paths))

    # If there is a hint that the action replaces the input, archive any inputs that are not in the result.
    if result.replaces_input and input_items:
        for input_store_path in old_inputs:
            current_workspace().archive(input_store_path)
            log.message("Archived input item: %s", input_store_path)

    # Select the final output and show the current selection.
    current_workspace().set_selection(new_outputs)
    commands.select()

    return result
