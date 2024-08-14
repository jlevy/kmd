import time
from typing import List, Optional, cast
from kmd.action_defs import look_up_action
from kmd.exec.system_actions import FETCH_PAGE_METADATA_NAME, fetch_page_metadata
from kmd.config.text_styles import EMOJI_CALL_BEGIN, EMOJI_CALL_END, EMOJI_TIMING
from kmd.file_storage.workspaces import current_workspace, ensure_saved
from kmd.lang_tools.inflection import plural
from kmd.model.actions_model import Action, ActionResult
from kmd.model.canon_url import canonicalize_url
from kmd.model.errors_model import InvalidInput, InvalidStoreState
from kmd.model.items_model import Item, State
from kmd.model.operations_model import Input, Operation, Source
from kmd.model.locators import Locator, StorePath, is_store_path
from kmd.text_formatting.text_formatting import format_lines
from kmd.util.type_utils import not_none
from kmd.config.logger import get_logger

log = get_logger(__name__)


def collect_args(*args: str) -> List[Locator]:
    if not args:
        try:
            selection_args = current_workspace().get_selection()
            return cast(List[Locator], selection_args)
        except InvalidStoreState:
            return []
    else:
        return cast(List[Locator], list(args))


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


def run_action(
    action: str | Action,
    *provided_args: str,
    internal_call=False,
    override_state: Optional[State] = None,
    rerun=False,
) -> ActionResult:
    """
    Main function to run an action.
    """

    start_time = time.time()

    # Get the action and action name.
    if not isinstance(action, Action):
        action = look_up_action(action)
    action_name = action.name

    # Get the current workspace params.
    ws = current_workspace()
    action_params = ws.get_params()

    # Update the action with any overridden params.
    log.info("Action params: %s", action_params)
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

    # Now we have the operation we will perform.
    # If the inputs are paths, record the input paths with hashes.
    # TODO: Also save the parameters/options that were used.
    inputs = [Input(StorePath(arg), ws.hash(StorePath(arg))) for arg in args if is_store_path(arg)]
    operation = Operation(action_name, inputs)
    log.message("%s Action: %s", EMOJI_CALL_BEGIN, operation.command_line())

    # Ensure input items are already saved in the workspace and load the corresponding items.
    # This also imports any URLs.
    input_items = [ensure_saved(arg) for arg in args]

    # Validate the precondition.
    action.validate_precondition(input_items)

    # URLs should have metadata like a title and be valid, so we fetch them.
    # We make an action call to do the fetch so need to avoid recursing.
    if action.name != FETCH_PAGE_METADATA_NAME:
        input_items = [fetch_url_items(item) for item in input_items]

    cached_result = None
    if not rerun:
        # Preassemble outputs, so we can check if they already exist.
        preassembled_result = action.preassemble(operation, input_items)
        if preassembled_result:
            # Check if these items already exist, with last_operation matching action and input fingerprints.
            already_present = [ws.find_by_id(item) for item in preassembled_result.items]
            if all(already_present):
                log.message(
                    "All outputs already saved so skipping action `%s`:\n%s",
                    action_name,
                    format_lines(already_present),
                )
                cached_items = [ws.load(not_none(store_path)) for store_path in already_present]
                cached_result = ActionResult(cached_items)

    if cached_result:
        # Use the cached result.
        result = cached_result

        result_store_paths = [StorePath(not_none(item.store_path)) for item in result.items]
        archived_store_paths = []

        log.message(
            "%s Action skipped: %s completed with %s %s",
            EMOJI_CALL_END,
            action_name,
            len(result.items),
            plural("item", len(result.items)),
        )
    else:
        # Run the action.
        result = action.run(input_items)

        # Record the operation and add to the history of each item.
        for i, item in enumerate(result.items):
            item.update_history(Source(operation=operation, output_num=i))

        # Override the state if requested (this handles marking items as transient).
        if override_state:
            for item in result.items:
                item.state = override_state

        # Save the result items. This is done here; the action itself should not worry about saving.
        for item in result.items:
            ws.save(item)

        input_store_paths = [StorePath(not_none(item.store_path)) for item in input_items]
        result_store_paths = [StorePath(not_none(item.store_path)) for item in result.items]
        old_inputs = sorted(set(input_store_paths) - set(result_store_paths))

        # If there is a hint that the action replaces the input, archive any inputs that are not in the result.
        ws = current_workspace()
        archived_store_paths = []
        if result.replaces_input and input_items:
            for input_store_path in old_inputs:
                # Note some outputs may be missing if replace_input was used.
                ws.archive(input_store_path, missing_ok=True)
                log.message("Archived input item: %s", input_store_path)
            archived_store_paths.extend(old_inputs)

        # Log info.
        log.info("Action `%s` result: %s", action_name, result)
        log.message(
            "%s Action done: %s completed with %s %s",
            EMOJI_CALL_END,
            action_name,
            len(result.items),
            plural("item", len(result.items)),
        )
        elapsed = time.time() - start_time
        if elapsed > 1.0:
            log.message("%s Action `%s` took %.1fs.", EMOJI_TIMING, action_name, elapsed)

    # Select the final output (omitting any that were archived).
    if not internal_call:
        final_outputs = sorted(set(result_store_paths) - set(archived_store_paths))
        ws.set_selection(final_outputs)

    return result
