from typing import Callable, List, Optional, Set, Tuple
from kmd.action_defs import look_up_action
from kmd.action_exec.action_exec import run_action
from kmd.action_exec.action_registry import (
    kmd_action_wrapped,
    no_wrapper,
    each_item_wrapper,
)
from kmd.config.text_styles import EMOJI_PROCESS
from kmd.file_storage.workspaces import current_workspace
from kmd.model.actions_model import Action, ActionInput, ActionResult
from kmd.config.logger import get_logger
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item, ItemRelations, ItemType, State
from kmd.model.locators import StorePath
from kmd.model.operations_model import OperationSummary
from kmd.text_formatting.html_in_md import (
    Wrapper,
    div_wrapper,
    identity_wrapper,
)
from kmd.text_ui.command_output import output_separator
from kmd.util.type_utils import not_none

log = get_logger(__name__)


def validate_action_names(action_names: List[str]) -> None:
    for action_name in action_names:
        look_up_action(action_name)


def define_action_sequence(
    name: str,
    action_names: list[str],
    description: Optional[str] = None,
    on_each_input: bool = False,
) -> None:
    """
    Register a sequential action that chains the outputs of each action to the inputs of the next.
    """

    if not action_names or len(action_names) <= 1:
        raise InvalidInput("Action must have at least two sub-actions: %s", action_names)

    extra_desc = "This action is a sequence of these actions: " + ", ".join(action_names) + "."
    seq_description = " ".join([description, extra_desc]) if description else extra_desc

    action_wrapper = each_item_wrapper if on_each_input else no_wrapper

    @kmd_action_wrapped(wrapper=action_wrapper)
    class SequenceAction(Action):
        def __init__(self):
            super().__init__(name=name, description=seq_description)

            self.action_sequence = action_names

        def run(self, items: ActionInput) -> ActionResult:
            log.message("%s Begin action sequence `%s`", EMOJI_PROCESS, self.name)

            validate_action_names(action_names)

            original_input_paths = [not_none(item.store_path) for item in items]
            transient_outputs: List[Item] = []

            for i, action_name in enumerate(self.action_sequence):
                for item in items:
                    if not item.store_path:
                        raise InvalidInput("Item must have a store path: %s", item)

                output_separator()
                log.message(
                    "%s Action sequence %s part %s of %s: %s",
                    EMOJI_PROCESS,
                    self.name,
                    i + 1,
                    len(self.action_sequence),
                    action_name,
                )

                item_paths = [not_none(item.store_path) for item in items]

                # Output of this action is transient if it's not the last action.
                last_action = i == len(self.action_sequence) - 1
                output_state = None if last_action else State.transient

                result = run_action(action_name, *item_paths, override_state=output_state)

                # Track transient items and archive them if all actions succeed.
                for item in result.items:
                    if item.state == State.transient:
                        transient_outputs.append(item)

                # Results are the input to the next action in the sequence.
                items = result.items

            # The final items should be derived from the original inputs.
            for item in items:
                item.update_relations(derived_from=original_input_paths)

            log.message("Sequence complete. Archiving transient items.")
            ws = current_workspace()
            for item in transient_outputs:
                assert item.store_path
                ws.archive(StorePath(item.store_path))

            output_separator()

            return ActionResult(items)


Combiner = Callable[[Action, List[Item], List[ActionResult]], Item]
"""A function that combines the outputs of multiple actions into a single Item."""


def combine_with_wrappers(
    action: Action,
    inputs: List[Item],
    results: List[ActionResult],
    wrappers: Optional[List[Wrapper]] = None,
    separator: str = "\n\n",
) -> Item:
    """
    Combine the outputs of multiple actions into a single item. Optionally wraps each item
    by calling a function on the body before combining.
    """

    if len(inputs) < 1:
        raise InvalidInput("Expected at least one input to combine: %s", inputs)
    if wrappers and len(wrappers) != len(results):
        raise InvalidInput("Expected as many wrappers as results: %s", wrappers)

    # Assemble the parts and wrappers.
    parts: List[Tuple[Item, Wrapper]] = []
    for i, result in enumerate(results):
        wrapper = wrappers[i] if wrappers else identity_wrapper
        for part in result.items:
            if not part.body:
                raise InvalidInput("Item result must have a body: %s", part)
            if not part.store_path:
                raise InvalidInput("Item result must have a store path: %s", part)

            parts.append((part, wrapper))

    # Assemble the body from the parts, wrapping each one.
    combo_body = separator.join(wrapper(not_none(part.body)) for part, wrapper in parts)

    combo_title = f"{inputs[0].title}"
    if len(inputs) > 1:
        combo_title += f" and {len(inputs) - 1} others"

    relations = ItemRelations(
        derived_from=[StorePath(not_none(part.store_path)) for part, _wrapper in parts]
    )
    combo_result = Item(
        title=combo_title,
        body=combo_body,
        type=ItemType.note,
        format=results[0].items[0].format,
        relations=relations,
    )

    # History when combining results is a litle complicated, so let's just concatenate
    # all the history lists but avoid duplicates.
    result_items = [item for result in results for item in result.items]
    unique_ops: Set[OperationSummary] = set()
    combo_result.history = []

    for item in result_items:
        for entry in item.history or []:
            if entry not in unique_ops:
                unique_ops.add(entry)
                combo_result.history.append(entry)

    return combo_result


def combine_as_paragraphs(action: Action, inputs: List[Item], results: List[ActionResult]) -> Item:
    """
    Combine the outputs of multiple actions into a single item, separating each part with
    paragraph breaks.
    """
    return combine_with_wrappers(action, inputs, results)


def combine_with_divs(*class_names: str) -> Combiner:
    """
    Combine the outputs of multiple actions into a single item, wrapping each part in a div with
    the corresponding name.
    """

    def combiner(action: Action, inputs: List[Item], results: List[ActionResult]) -> Item:
        wrappers = [div_wrapper(class_name, padding="\n\n") for class_name in class_names]
        return combine_with_wrappers(action, inputs, results, wrappers)

    return combiner


def define_action_combo(
    name,
    action_names: List[str],
    description: Optional[str] = None,
    combiner: Combiner = combine_as_paragraphs,
    on_each_input: Optional[bool] = False,
) -> None:
    """
    Register an action that combines the results of other actions.
    """

    if not action_names or len(action_names) <= 1:
        raise InvalidInput("Action must have at least two sub-actions: %s", action_names)

    extra_desc = "This action combines outputs of these actions: " + ", ".join(action_names) + "."
    combo_description = " ".join([description, extra_desc]) if description else extra_desc

    action_wrapper = each_item_wrapper if on_each_input else no_wrapper

    @kmd_action_wrapped(wrapper=action_wrapper)
    class ComboAction(Action):
        def __init__(self):
            super().__init__(name=name, description=combo_description)
            self.action_sequence = action_names
            self.combiner = combiner

        def run(self, items: ActionInput) -> ActionResult:
            validate_action_names(action_names)

            for item in items:
                if not item.store_path:
                    raise InvalidInput("Item must have a store path: %s", item)

            item_paths = [not_none(item.store_path) for item in items]

            results: List[ActionResult] = []

            for i, action_name in enumerate(self.action_sequence):
                output_separator()
                log.message(
                    "%s Action combo %s part %s of %s: %s",
                    EMOJI_PROCESS,
                    self.name,
                    i + 1,
                    len(self.action_sequence),
                    action_name,
                )

                result = run_action(action_name, *item_paths, override_state=State.transient)

                results.append(result)

            combined_result = self.combiner(self, items, results)

            output_separator()

            log.message(
                "Combined output of %s actions on %s inputs: %s",
                len(results),
                len(items),
                combined_result,
            )

            return ActionResult([combined_result])
