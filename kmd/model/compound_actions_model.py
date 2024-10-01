from dataclasses import field
from typing import List, Optional

from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.combiners import Combiner
from kmd.model.actions_model import Action, ActionInput, ActionResult
from kmd.model.items_model import Item, State
from kmd.model.paths_model import StorePath
from kmd.util.task_stack import task_stack
from kmd.util.type_utils import not_none

log = get_logger(__name__)


def look_up_actions(action_names: List[str]) -> List[Action]:
    from kmd.action_defs import look_up_action

    return [look_up_action(action_name) for action_name in action_names]


@dataclass
class SequenceAction(Action):
    """
    A sequential action that chains the outputs of each action to the inputs of the next.
    """

    action_names: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.action_names or len(self.action_names) <= 1:
            raise InvalidInput(
                f"Action must have at least two sub-actions: {self.name}: {self.action_names}"
            )

        extra_desc = "This action is a sequence of these actions:\n\n" + ", ".join(
            f"`{name}`" for name in self.action_names
        )
        seq_description = (
            "\n\n".join([self.description, extra_desc]) if self.description else extra_desc
        )
        self.description = seq_description

    def run(self, items: ActionInput) -> ActionResult:
        from kmd.exec.action_exec import run_action
        from kmd.file_storage.workspaces import current_workspace

        with task_stack().context(self.name, total_parts=len(self.action_names), unit="step") as ts:

            look_up_actions(self.action_names)  # Validate action names.

            log.message("Begin action sequence `%s`", self.name)

            original_input_paths = [not_none(item.store_path) for item in items]
            transient_outputs: List[Item] = []

            for i, action_name in enumerate(self.action_names):

                for item in items:
                    if not item.store_path:
                        raise InvalidInput("Item must have a store path: %s", item)

                log.message(
                    "Action sequence `%s` step %s/%s: `%s`",
                    self.name,
                    i + 1,
                    len(self.action_names),
                    action_name,
                )

                item_paths = [not_none(item.store_path) for item in items]

                # Output of this action is transient if it's not the last action.
                last_action = i == len(self.action_names) - 1
                output_state = None if last_action else State.transient

                # Run this action.
                result = run_action(action_name, *item_paths, override_state=output_state)

                # Track transient items and archive them if all actions succeed.
                for item in result.items:
                    if item.state == State.transient:
                        transient_outputs.append(item)

                # Results are the input to the next action in the sequence.
                items = result.items

                ts.next()

            # The final items should be derived from the original inputs.
            for item in items:
                if item.store_path in original_input_paths:
                    # Special case in case an action does nothing to an item.
                    log.info("Result item is an original input: %s", item.store_path)
                else:
                    item.update_relations(derived_from=original_input_paths)

            log.message("Action sequence `%s` complete. Archiving transient items.", self.name)
            ws = current_workspace()
            for item in transient_outputs:
                try:
                    ws.archive(StorePath(not_none(item.store_path)))
                except FileNotFoundError:
                    log.info("Item to archive not found, moving on: %s", item.store_path)

        return ActionResult(items)


@dataclass
class ComboAction(Action):
    """
    An action that combines the results of other actions.
    """

    action_names: List[str] = field(default_factory=list)
    combiner: Optional[Combiner] = field(default=None)

    def __post_init__(self):
        if not self.action_names or len(self.action_names) <= 1:
            raise InvalidInput(
                f"Action must have at least two sub-actions: {self.name}: {self.action_names}"
            )

        extra_desc = "This action is a combination of these actions:\n\n" + ", ".join(
            f"`{name}`" for name in self.action_names
        )
        combo_description = (
            "\n\n".join([self.description, extra_desc]) if self.description else extra_desc
        )

        self.description = combo_description

    def run(self, items: ActionInput) -> ActionResult:
        from kmd.exec.action_exec import run_action
        from kmd.exec.combiners import combine_as_paragraphs

        with task_stack().context(self.name, total_parts=len(self.action_names), unit="part") as ts:

            look_up_actions(self.action_names)  # Validate action names.

            for item in items:
                if not item.store_path:
                    raise InvalidInput("Item must have a store path: %s", item)

            item_paths = [not_none(item.store_path) for item in items]

            results: List[ActionResult] = []

            for i, action_name in enumerate(self.action_names):

                log.message(
                    "Action combo `%s` part %s/%s: %s",
                    self.name,
                    i + 1,
                    len(self.action_names),
                    action_name,
                )

                result = run_action(action_name, *item_paths, override_state=State.transient)

                results.append(result)

                ts.next()

            combiner = self.combiner or combine_as_paragraphs
            combined_result = combiner(self, items, results)

        log.message(
            "Combined output of %s actions on %s inputs: %s",
            len(results),
            len(items),
            combined_result,
        )

        return ActionResult([combined_result])
