import time
from dataclasses import replace
from typing import List, Optional

from kmd.action_defs import look_up_action
from kmd.config.logger import get_logger
from kmd.config.text_styles import EMOJI_SKIP, EMOJI_SUCCESS, EMOJI_TIMING
from kmd.errors import ContentError, InvalidInput, InvalidOutput, NONFATAL_EXCEPTIONS
from kmd.exec.resolve_args import assemble_action_args
from kmd.exec.system_actions import fetch_page_metadata
from kmd.lang_tools.inflection import plural
from kmd.model.actions_model import (
    Action,
    ActionInput,
    ActionResult,
    NO_ARGS,
    PathOpType,
    PerItemAction,
)
from kmd.model.canon_url import canonicalize_url
from kmd.model.items_model import Item, State
from kmd.model.operations_model import Input, Operation, Source
from kmd.model.paths_model import StorePath
from kmd.util.format_utils import fmt_lines
from kmd.util.task_stack import task_stack
from kmd.util.type_utils import not_none
from kmd.workspaces.selections import Selection
from kmd.workspaces.workspace_importing import import_and_load
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


def fetch_url_items(item: Item) -> Item:
    if not item.url or not item.is_url_resource():
        return item

    if not item.store_path:
        raise InvalidInput(f"URL item should already be stored: {item}")

    if item.title and item.description:
        # Already have metadata.
        return item

    item.url = canonicalize_url(item.url)
    log.message("No metadata for URL, will fetch: %s", item.url)
    enriched_item = run_action(
        fetch_page_metadata, StorePath(item.store_path).display_str(), internal_call=True
    )
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
    ws_params = ws.params.get_values()

    # Fill in the action with any overridden params.
    log.info("Parameters from workspace:\n%s", ws_params.as_str())
    action = action.with_param_values(ws_params, strict=False, overwrite=False)

    # Collect args from the provided args or otherwise the current selection.
    args, from_selection = assemble_action_args(*provided_args, use_selection=action.uses_selection)

    # As a special case for convenience, if the action expects no args, ignore any pre-selected inputs.
    if action.expected_args == NO_ARGS and from_selection:
        log.message("Ignoring selection since action `%s` expects no args.", action_name)
        args.clear()

    if args:
        source_str = "provided args" if provided_args else "selection"
        log.message(
            "Using %s as inputs to action `%s`:\n%s", source_str, action_name, fmt_lines(args)
        )

    # Ensure we have the right number of args.
    action.validate_args(args)

    # Ensure input items are already saved in the workspace and load the corresponding items.
    # This also imports any URLs.
    input_items = [import_and_load(ws, arg) for arg in args]

    # Now make a note of the the operation we will perform.
    # If the inputs are paths, record the input paths with hashes.
    # TODO: Also save the parameters/options that were used.
    store_paths = [StorePath(not_none(item.store_path)) for item in input_items if item.store_path]
    inputs = [Input(store_path, ws.hash(store_path)) for store_path in store_paths]
    operation = Operation(action_name, inputs, action.param_value_summary())

    log.message("Action:\n%s", fmt_lines([f"`{operation.command_line(with_options=False)}`"]))
    if len(action.param_value_summary()) > 0:
        log.message("%s", action.param_value_summary_str())
    log.info("Operation is: %s", operation)
    log.info("Input items are:\n%s", fmt_lines(input_items))

    # Validate the precondition.
    action.validate_precondition(input_items)

    # URLs should have metadata like a title and be valid, so we fetch them.
    # We make an action call to do the fetch so need to avoid recursing.
    if action.name != fetch_page_metadata.name:
        if input_items:
            log.message("Assembling metadata for input items:\n%s", fmt_lines(input_items))
            input_items = [fetch_url_items(item) for item in input_items]

    existing_result = None

    # Check if a previous run already produced the result.
    # To do this we preassemble outputs.
    preassembled_result = action.preassemble(operation, input_items)
    if preassembled_result:
        # Check if these items already exist, with last_operation matching action and input fingerprints.
        already_present = [ws.find_by_id(item) for item in preassembled_result.items]
        all_present = all(already_present)
        log.info(
            "Rerun check: all_present=%s with these items already present:\n%s",
            all_present,
            fmt_lines(already_present),
        )
        if all_present:
            if rerun:
                log.message("All outputs already exist but running anyway since rerun requested.")
            else:
                log.message(
                    "All outputs already exist! Skipping action (use --rerun to force run).",
                )
                existing_items = [ws.load(not_none(store_path)) for store_path in already_present]
                existing_result = ActionResult(existing_items)
    else:
        log.info(
            "Rerun check: Will run since `%s` has no rerun check (no preassembly).",
            action_name,
        )

    if existing_result:
        # Use the cached result.
        result = existing_result

        result_store_paths = [StorePath(not_none(item.store_path)) for item in result.items]
        archived_store_paths = []

        log.message(
            "%s Action skipped: `%s` completed with %s %s",
            EMOJI_SKIP,
            action_name,
            len(result.items),
            plural("item", len(result.items)),
        )
    else:
        # Run the action.
        if action.run_per_item:
            result = run_for_each_item(action, input_items)
        else:
            result = action.run(input_items)

        if not result:
            raise InvalidOutput(f"Action `{action_name}` did not return any results")

        # Record the operation and add to the history of each item.
        was_run_for_each = isinstance(action, PerItemAction)
        for i, item in enumerate(result.items):
            # PerItemAction should be treated as if they ran on each item individually.
            if was_run_for_each:
                this_op = replace(operation, arguments=[operation.arguments[i]])
            else:
                this_op = operation
            item.update_history(Source(operation=this_op, output_num=i, cacheable=action.cacheable))

        # Override the state if requested (this handles marking items as transient).
        if override_state:
            for item in result.items:
                item.state = override_state

        # Save the result items. This is done here; the action itself should not worry about saving.
        skipped_paths = []
        for item in result.items:
            if result.skip_duplicates:
                store_path = ws.find_by_id(item)
                if store_path:
                    skipped_paths.append(store_path)
                    continue

            ws.save(item)

        if skipped_paths:
            log.message(
                "Skipped saving %s items already saved:\n%s",
                len(skipped_paths),
                fmt_lines(skipped_paths),
            )

        input_store_paths = [StorePath(not_none(item.store_path)) for item in input_items]
        result_store_paths = [
            StorePath(item.store_path) for item in result.items if item.store_path
        ]
        old_inputs = sorted(set(input_store_paths) - set(result_store_paths))
        log.info("result_store_paths:\n%s", fmt_lines(result_store_paths))
        log.info("old_inputs:\n%s", fmt_lines(old_inputs))

        # If there is a hint that the action replaces the input, archive any inputs that are not in the result.
        ws = current_workspace()
        archived_store_paths = []
        if result.replaces_input and input_items:
            for input_store_path in old_inputs:
                # Note some outputs may be missing if replace_input was used.
                ws.archive(input_store_path, missing_ok=True)
            log.message(
                "Archived old input items since action replaces input: %s",
                fmt_lines(old_inputs),
            )
            archived_store_paths.extend(old_inputs)

        # Log info.
        log.info("Action `%s` result: %s", action_name, result)
        log.message(
            "%s Action done: `%s` completed with %s %s",
            EMOJI_SUCCESS,
            action_name,
            len(result.items),
            plural("item", len(result.items)),
        )
        elapsed = time.time() - start_time
        if elapsed > 1.0:
            log.message("%s Action `%s` took %.1fs.", EMOJI_TIMING, action_name, elapsed)

    # Implement any path operations from the output and/or select the final output
    if not internal_call:
        if result.path_ops:
            path_ops = [
                path_op
                for path_op in result.path_ops
                if path_op.store_path not in archived_store_paths
            ]

            path_op_archive = [
                path_op.store_path for path_op in path_ops if path_op.op == PathOpType.archive
            ]
            if path_op_archive:
                log.message("Archiving %s items based on action result.", len(path_op_archive))
                for store_path in path_op_archive:
                    ws.archive(store_path, missing_ok=True)

            path_op_selection = [
                path_op.store_path for path_op in path_ops if path_op.op == PathOpType.select
            ]
            if path_op_selection:
                log.message("Selecting %s items based on action result.", len(path_op_selection))
                ws.selections.push(Selection(paths=path_op_selection))
        else:
            # Otherwise if no path_ops returned, default behavior is to select the final
            # outputs (omitting any that were archived).
            final_outputs = sorted(set(result_store_paths) - set(archived_store_paths))
            log.info("final_outputs:\n%s", fmt_lines(final_outputs))
            ws.selections.push(Selection(paths=final_outputs))

    return result


def run_for_each_item(action: Action, items: ActionInput) -> ActionResult:
    """
    Process each input item. If non-fatal errors are encountered on any item,
    they are reported and processing continues with the next item.
    """

    log.message("Running action `%s` for each input on %s items", action.name, len(items))

    def run_item(item: Item) -> Item:
        # Should have already validated arg counts by now.
        result = action.run([item])
        if result.has_hints():
            log.warning(
                "Ignoring result hints for action `%s` when running on multiple items"
                " (consider setting run_per_item=False): %s",
                action.name,
                result,
            )
        return result.items[0]

    with task_stack().context(action.name, len(items), "item") as ts:
        result_items: List[Item] = []
        errors: List[Exception] = []
        multiple_inputs = len(items) > 1

        for i, item in enumerate(items):
            log.message(
                "Action `%s` input item %d/%d:\n%s",
                action.name,
                i + 1,
                len(items),
                fmt_lines([item]),
            )
            had_error = False
            try:
                result_item = run_item(item)
                result_items.append(result_item)
                had_error = False
            except NONFATAL_EXCEPTIONS as e:
                errors.append(e)
                had_error = True

                if multiple_inputs:
                    log.error(
                        "Error processing item; continuing with others: %s: %s",
                        e,
                        item,
                    )
                else:
                    # If there's only one input, fail fast.
                    raise e
            finally:
                ts.next(last_had_error=had_error)

    if errors:
        log.error(
            "%s %s occurred while processing items. See above!",
            len(errors),
            plural("error", len(errors)),
        )

    if len(result_items) < 1:
        raise ContentError(f"Action `{action.name}` returned no items")

    return ActionResult(result_items)
