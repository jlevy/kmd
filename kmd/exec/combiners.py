from typing import Callable, List, Optional, Set, Tuple
from kmd.model.actions_model import Action, ActionResult
from kmd.config.logger import get_logger
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item, ItemRelations, ItemType
from kmd.model.locators import StorePath
from kmd.model.operations_model import OperationSummary
from kmd.text_formatting.html_in_md import (
    Wrapper,
    div_wrapper,
    identity_wrapper,
)
from kmd.util.type_utils import not_none

log = get_logger(__name__)


Combiner = Callable[[Action, List[Item], List[ActionResult]], Item]
"""A function that combines the outputs of multiple actions into a single Item."""


def combine_with_wrappers(
    inputs: List[Item],
    results: List[ActionResult],
    wrappers: Optional[List[Wrapper]] = None,
    separator: str = "\n\n",
) -> Item:
    """
    Combine the outputs of multiple actions into a single item. Optionally wraps each item
    by calling a function on the body before combining. Returns final combined item.
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


def combine_as_paragraphs(_action: Action, inputs: List[Item], results: List[ActionResult]) -> Item:
    """
    Combine the outputs of multiple actions into a single item, separating each part with
    paragraph breaks.
    """
    return combine_with_wrappers(inputs, results)


def combine_with_divs(*class_names: str) -> Combiner:
    """
    Combine the outputs of multiple actions into a single item, wrapping each part in a div with
    the corresponding name.
    """

    def combiner(_action: Action, inputs: List[Item], results: List[ActionResult]) -> Item:
        wrappers = [div_wrapper(class_name, padding="\n\n") for class_name in class_names]
        return combine_with_wrappers(inputs, results, wrappers)

    return combiner
