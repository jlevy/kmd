from typing import List, cast
from strif import abbreviate_str
from kmd.actions.action_registry import load_all_actions
from kmd.file_storage.file_store import NoSelectionError
from kmd.file_storage.workspaces import current_workspace, ensure_saved
from kmd.model.actions_model import Action, ActionResult
from kmd.model.locators import StorePath
from kmd.text_handling.text_formatting import format_lines
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
        log.message(
            f"Using provided args as inputs to action %s:\n%s",
            action_name,
            format_lines(provided_args),
        )
    elif args:
        log.message(f"Using selection as inputs to action %s:\n%s", action_name, format_lines(args))

    # Ensure we have the right number of args.
    action.validate_args(args)

    log.message(
        "≫ Action: %s %s",
        action_name,
        abbreviate_str(" ".join(repr(arg) for arg in args), max_len=200),
    )

    # Ensure any items that are not saved are already in the workspace and get the corresponding items.
    # This looks up any URLs.
    input_items = [ensure_saved(arg) for arg in args]

    # Run the action.
    result = action.run(input_items)

    log.info("Run action: Result: %s", result)
    log.message(f"≪ Action done: %s completed with %s items", action_name, len(result.items))

    # Save the result items. This is done here so the action need not worry about saving.
    for item in result.items:
        current_workspace().save(item)

    input_store_paths = [StorePath(not_none(item.store_path)) for item in input_items]
    result_store_paths = [StorePath(not_none(item.store_path)) for item in result.items]
    old_inputs = sorted(set(input_store_paths) - set(result_store_paths))

    # If there is a hint that the action replaces the input, archive any inputs that are not in the result.
    archived_store_paths = []
    if result.replaces_input and input_items:
        for input_store_path in old_inputs:
            current_workspace().archive(input_store_path)
            log.message("Archived input item: %s", input_store_path)
        archived_store_paths = old_inputs

    # Select the final output (omitting any that were archived) and show the current selection.
    remaining_outputs = sorted(set(result_store_paths) - set(archived_store_paths))
    current_workspace().set_selection(remaining_outputs)
    commands.select()

    return result
