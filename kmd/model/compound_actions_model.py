from typing import List, Optional

from kmd.config.logger import get_logger
from kmd.exec.combiners import combine_as_paragraphs, Combiner
from kmd.model.actions_model import Action, ActionInput, ActionResult
from kmd.model.arguments_model import StorePath
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item, ItemType, State
from kmd.model.operations_model import Operation
from kmd.model.preconditions_model import Precondition
from kmd.util.task_stack import task_stack
from kmd.util.type_utils import not_none


log = get_logger(__name__)


def look_up_actions(action_names: List[str]) -> List[Action]:
    from kmd.action_defs import look_up_action

    return [look_up_action(action_name) for action_name in action_names]


class SequenceAction(Action):
    """
    A sequential action that chains the outputs of each action to the inputs of the next.
    """

    def __init__(
        self,
        name: str,
        action_names: List[str],
        description: Optional[str] = None,
        precondition: Optional[Precondition] = None,
    ):
        if not action_names or len(action_names) <= 1:
            raise InvalidInput("Action must have at least two sub-actions: %s", action_names)

        extra_desc = "This action is a sequence of these actions:\n\n" + ", ".join(
            f"`{name}`" for name in action_names
        )
        seq_description = "\n\n".join([description, extra_desc]) if description else extra_desc

        super().__init__(name=name, description=seq_description, precondition=precondition)

        self.action_names = action_names

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
                    "Action sequence `%s` step %s of %s: `%s`",
                    self.name,
                    i + 1,
                    len(self.action_names),
                    action_name,
                )

                item_paths = [not_none(item.store_path) for item in items]

                # Output of this action is transient if it's not the last action.
                last_action = i == len(self.action_names) - 1
                output_state = None if last_action else State.transient

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
                item.update_relations(derived_from=original_input_paths)

            log.message("Action sequence `%s` complete. Archiving transient items.", self.name)
            ws = current_workspace()
            for item in transient_outputs:
                assert item.store_path
                ws.archive(StorePath(item.store_path))

        return ActionResult(items)


class CachedDocSequence(SequenceAction):
    """
    A sequence with a single doc output that allows rerun checking.
    """

    # Implementing this makes caching work.
    def preassemble(self, operation: Operation, items: ActionInput) -> Optional[ActionResult]:
        return ActionResult(
            [self.preassemble_one(operation, items, output_num=0, type=ItemType.doc)]
        )


class ComboAction(Action):
    """
    An action that combines the results of other actions.
    """

    def __init__(
        self,
        name: str,
        action_names: List[str],
        description: Optional[str] = None,
        combiner: Combiner = combine_as_paragraphs,
        precondition: Optional[Precondition] = None,
    ):

        if not action_names or len(action_names) <= 1:
            raise InvalidInput("Action must have at least two sub-actions: %s", action_names)

        extra_desc = "This action is a combination of these actions:\n\n" + ", ".join(
            f"`{name}`" for name in action_names
        )
        combo_description = "\n\n".join([description, extra_desc]) if description else extra_desc

        super().__init__(name=name, description=combo_description, precondition=precondition)

        self.action_names = action_names
        self.combiner = combiner

    def run(self, items: ActionInput) -> ActionResult:
        from kmd.exec.action_exec import run_action

        with task_stack().context(self.name, total_parts=len(self.action_names), unit="part") as ts:

            look_up_actions(self.action_names)  # Validate action names.

            for item in items:
                if not item.store_path:
                    raise InvalidInput("Item must have a store path: %s", item)

            item_paths = [not_none(item.store_path) for item in items]

            results: List[ActionResult] = []

            for i, action_name in enumerate(self.action_names):

                log.message(
                    "Action combo `%s`: Part %s of %s: %s",
                    self.name,
                    i + 1,
                    len(self.action_names),
                    action_name,
                )

                result = run_action(action_name, *item_paths, override_state=State.transient)

                results.append(result)

                ts.next()

            combined_result = self.combiner(self, items, results)

        log.message(
            "Combined output of %s actions on %s inputs: %s",
            len(results),
            len(items),
            combined_result,
        )

        return ActionResult([combined_result])


class CachedDocCombo(ComboAction):
    """
    A combo action with a single doc output that allows rerun checking.
    """

    # Implementing this makes caching work.
    def preassemble(self, operation: Operation, items: ActionInput) -> Optional[ActionResult]:
        return ActionResult(
            [self.preassemble_one(operation, items, output_num=0, type=ItemType.doc)]
        )
