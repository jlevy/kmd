from typing import List, cast
from strif import abbreviate_str
from kmd.actions.action_registry import look_up_action
from kmd.actions.system_actions import FETCH_ACTION, FETCH_ACTION_NAME
from kmd.file_storage.workspaces import current_workspace, ensure_saved
from kmd.model.actions_model import Action, ActionResult
from kmd.model.canon_url import canonicalize_url
from kmd.model.errors_model import InvalidInput, InvalidStoreState
from kmd.model.items_model import Item
from kmd.model.locators import StorePath
from kmd.text_formatting.text_formatting import format_lines
from kmd.util.parse_utils import format_key_value
from kmd.util.type_utils import not_none
from kmd.commands import commands
from kmd.config.logger import get_logger

log = get_logger(__name__)


def collect_args(*args: str) -> List[str]:
    if not args:
        try:
            selection_args = current_workspace().get_selection()
            return cast(List[str], selection_args)
        except InvalidStoreState:
            return []
    else:
        return list(args)


def fetch_url_items(item: Item) -> Item:
    if not item.url or not item.is_url_resource():
        return item

    if not item.store_path:
        raise InvalidInput("URL item should already be stored: %s", item)

    item.url = canonicalize_url(item.url)
    log.message("Fetching URL for metadata: %s", item.url)
    enriched_item = run_action(FETCH_ACTION, item.store_path, internal_call=True)
    return enriched_item.items[0]


def run_action(action: str | Action, *provided_args: str, internal_call=False) -> ActionResult:

    # Get the action and action name.
    if not isinstance(action, Action):
        action = look_up_action(action)
    action_name = action.name

    # Get the current action params.
    workspace = current_workspace()
    action_params = workspace.get_action_params()

    # Update the action with any overridden params.
    if action_params:
        action = action.update_with_params(action_params)
        log.message(
            "Parameters apply to action %s:\n%s",
            action_name,
            format_lines(format_key_value(key, value) for key, value in action_params.items()),
        )

    # Collect args from the provided args or otherwise the current selection.
    args = collect_args(*provided_args)
    if args:
        source_str = "provided args" if provided_args else "selection"
        log.message(
            "Using %s as inputs to action %s:\n%s", source_str, action_name, format_lines(args)
        )

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

    # URLs should have metadata like a title and be valid, so we fetch them.
    # Note we call ourselves to do the fetch.
    if action.name != FETCH_ACTION_NAME:
        input_items = [fetch_url_items(item) for item in input_items]

    # Run the action.
    result = action.run(input_items)

    log.info("Run action: Result: %s", result)
    log.message(f"≪ Action done: %s completed with %s items", action_name, len(result.items))

    # Save the result items. This is done here so the action need not worry about saving.
    for item in result.items:
        workspace.save(item)

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
    if not internal_call:
        remaining_outputs = sorted(set(result_store_paths) - set(archived_store_paths))
        current_workspace().set_selection(remaining_outputs)
        commands.select()

    return result
