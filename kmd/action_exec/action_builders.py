from typing import Callable, List, Optional
from kmd.action_defs import look_up_action, reload_actions
from kmd.action_exec.action_exec import run_action
from kmd.action_exec.action_registry import kmd_action
from kmd.action_exec.llm_action_base import LLMAction
from kmd.config.text_styles import EMOJI_PROCESS
from kmd.model.actions_model import Action, ActionInput, ActionResult
from kmd.config.logger import get_logger
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item, ItemRelations, ItemType
from kmd.model.locators import StorePath
from kmd.util.type_utils import not_none

log = get_logger(__name__)


def define_llm_action(
    name,
    friendly_name,
    description,
    model,
    system_message,
    title_template,
    template,
    windowing=None,
    diff_filter=None,
):
    """
    Convenience method to register an LLM action.
    """

    @kmd_action
    class CustomLLMAction(LLMAction):
        def __init__(self):
            super().__init__(
                name,
                friendly_name,
                description,
                model=model,
                system_message=system_message,
                title_template=title_template,
                template=template,
                windowing=windowing,
                diff_filter=diff_filter,
            )


def _validate_action_names(action_names: List[str]) -> None:
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
            _validate_action_names(action_names)

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


def combine_outputs_default(
    action: Action,
    inputs: List[Item],
    results: List[ActionResult],
    separator: str = "\n\n",
) -> Item:
    """
    Combine the outputs of multiple actions into a single item using paragraph breaks.
    """

    if len(inputs) < 1:
        raise InvalidInput("Expect at least one input to combine: %s", inputs)

    parts = []
    for result in results:
        for part in result.items:
            if not part.body:
                raise InvalidInput("Item result must have a body: %s", part)
            if not part.store_path:
                raise InvalidInput("Item result must have a store path: %s", part)

            parts.append(part)

    combo_body = separator.join(part.body for part in parts)

    combo_title = f"{inputs[0].title}"
    if len(inputs) > 1:
        combo_title += f" and {len(inputs) - 1} others"
    combo_title += f" ({action.friendly_name})"

    relations = ItemRelations(derived_from=[StorePath(part.store_path) for part in parts])
    combo_result = Item(
        title=combo_title,
        body=combo_body,
        type=ItemType.note,
        format=results[0].items[0].format,
        relations=relations,
    )

    return combo_result


def define_action_combo(
    name,
    action_names: List[str],
    friendly_name: Optional[str] = None,
    description: Optional[str] = None,
    combiner: Combiner = combine_outputs_default,
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
            _validate_action_names(action_names)

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
