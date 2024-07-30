import time
from typing import List, cast
from strif import abbreviate_str
from kmd.action_defs import look_up_action
from kmd.action_exec.system_actions import FETCH_PAGE_METADATA_NAME, fetch_page_metadata
from kmd.text_ui.command_output import output
from kmd.config.text_styles import EMOJI_CALL_BEGIN, EMOJI_CALL_END, EMOJI_TIMING
from kmd.file_storage.workspaces import current_workspace, ensure_saved
from kmd.lang_tools.inflection import plural
from kmd.model.actions_model import Action, ActionResult
from kmd.model.canon_url import canonicalize_url
from kmd.model.errors_model import InvalidInput, InvalidStoreState
from kmd.model.items_model import Item
from kmd.model.locators import StorePath
from kmd.text_formatting.text_formatting import format_lines
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

    if item.title and item.description:
        # Already have metadata.
        return item

    item.url = canonicalize_url(item.url)
    log.message("No metadata for URL, will fetch: %s", item.url)
    enriched_item = run_action(fetch_page_metadata, item.store_path, internal_call=True)
    return enriched_item.items[0]


def run_action(action: str | Action, *provided_args: str, internal_call=False) -> ActionResult:

    start_time = time.time()

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
        "%s Action: %s %s",
        EMOJI_CALL_BEGIN,
        action_name,
        abbreviate_str(" ".join(repr(arg) for arg in args), max_len=200),
    )

    # Ensure any items that are not saved are already in the workspace and get the corresponding items.
    # This looks up any URLs.
    input_items = [ensure_saved(arg) for arg in args]

    # URLs should have metadata like a title and be valid, so we fetch them.
    # We make an action call to do the fetch so need to avoid recursing.
    if action.name != FETCH_PAGE_METADATA_NAME:
        input_items = [fetch_url_items(item) for item in input_items]

    # Run the action.
    result = action.run(input_items)

    elapsed = time.time() - start_time

    log.info("Action %s result: %s", action_name, result)
    log.message(
        "%s Action done: %s completed with %s %s",
        EMOJI_CALL_END,
        action_name,
        len(result.items),
        plural("item", len(result.items)),
    )
    if elapsed > 1.0:
        log.message("%s Action %s took %.1fs.", EMOJI_TIMING, action_name, elapsed)

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
        output()
        commands.select()

    return result
