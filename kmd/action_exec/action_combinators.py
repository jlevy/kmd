from typing import Callable, List, Optional
from kmd.action_defs import look_up_action
from kmd.action_exec.action_exec import run_action
from kmd.action_exec.action_registry import kmd_action
from kmd.config.text_styles import EMOJI_PROCESS
from kmd.model.actions_model import Action, ActionInput, ActionResult
from kmd.config.logger import get_logger
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item, ItemRelations, ItemType
from kmd.model.locators import StorePath
from kmd.text_formatting.html_in_md import (
    Wrapper,
    div_wrapper,
    identity_wrapper,
)
from kmd.util.type_utils import not_none

log = get_logger(__name__)


def validate_action_names(action_names: List[str]) -> None:
    for action_name in action_names:
        look_up_action(action_name)


def define_action_sequence(
    name: str,
    action_names: list[str],
    friendly_name: Optional[str] = None,
    description: Optional[str] = None,
) -> None:
    """
    Register an action that combines the results of other actions.
    """

    if not action_names or len(action_names) <= 1:
        raise InvalidInput("Action must have at least two sub-actions: %s", action_names)

    seq_friendly_name = friendly_name or name
    extra_desc = "This action is a sequence of these actions: " + ", ".join(action_names) + "."
    seq_description = " ".join([description, extra_desc]) if description else extra_desc

    @kmd_action
    class SequenceAction(Action):
        def __init__(self):
            super().__init__(
                name=name, friendly_name=seq_friendly_name, description=seq_description
            )

            self.action_sequence = action_names

        def run(self, items: ActionInput) -> ActionResult:
            validate_action_names(action_names)

            for i, action_name in enumerate(self.action_sequence):
                for item in items:
                    if not item.store_path:
                        raise InvalidInput("Item must have a store path: %s", item)

                log.separator()
                log.message(
                    "%s Action sequence %s part %s of %s: %s",
                    EMOJI_PROCESS,
                    self.name,
                    i + 1,
                    len(self.action_sequence),
                    action_name,
                )

                item_paths = [not_none(item.store_path) for item in items]
                result = run_action(action_name, *item_paths)
                items = result.items

            log.separator()

            return ActionResult(items)


Combiner = Callable[[Action, List[Item], List[ActionResult]], Item]
"""
A function that combines the outputs of multiple actions into a single Item.
"""


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

    parts = []
    for i, result in enumerate(results):
        wrapper = wrappers[i] if wrappers else identity_wrapper
        for part in result.items:
            if not part.body:
                raise InvalidInput("Item result must have a body: %s", part)
            if not part.store_path:
                raise InvalidInput("Item result must have a store path: %s", part)

            parts.append((part, wrapper))

    combo_body = separator.join(wrapper(part.body) for part, wrapper in parts)

    combo_title = f"{inputs[0].title}"
    if len(inputs) > 1:
        combo_title += f" and {len(inputs) - 1} others"
    combo_title += f" ({action.friendly_name})"

    relations = ItemRelations(derived_from=[StorePath(part.store_path) for part, _wrapper in parts])
    combo_result = Item(
        title=combo_title,
        body=combo_body,
        type=ItemType.note,
        format=results[0].items[0].format,
        relations=relations,
    )

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
        return combine_with_wrappers(
            action, inputs, results, [div_wrapper(class_name) for class_name in class_names]
        )

    return combiner


def define_action_combo(
    name,
    action_names: List[str],
    friendly_name: Optional[str] = None,
    description: Optional[str] = None,
    combiner: Combiner = combine_as_paragraphs,
) -> None:
    """
    Register an action that combines the results of other actions.
    """

    if not action_names or len(action_names) <= 1:
        raise InvalidInput("Action must have at least two sub-actions: %s", action_names)

    combo_friendly_name = friendly_name or name
    extra_desc = "This action combines outputs of these actions: " + ", ".join(action_names) + "."
    combo_description = " ".join([description, extra_desc]) if description else extra_desc

    @kmd_action
    class ComboAction(Action):
        def __init__(self):
            super().__init__(
                name=name, friendly_name=combo_friendly_name, description=combo_description
            )
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
                log.separator()
                log.message(
                    "%s Action combo %s part %s of %s: %s",
                    EMOJI_PROCESS,
                    self.name,
                    i + 1,
                    len(self.action_sequence),
                    action_name,
                )

                result = run_action(action_name, *item_paths)

                results.append(result)

            combined_result = self.combiner(self, items, results)

            log.separator()

            log.message(
                "Combined output of %s actions on %s inputs: %s",
                len(results),
                len(items),
                combined_result,
            )

            return ActionResult([combined_result])
