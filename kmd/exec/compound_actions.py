from typing import List, Optional
from kmd.action_defs import look_up_action
from kmd.exec.action_exec import run_action
from kmd.config.text_styles import EMOJI_ACTION
from kmd.file_storage.workspaces import current_workspace
from kmd.model.actions_model import Action, ActionInput, ActionResult
from kmd.config.logger import get_logger
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item, State
from kmd.model.locators import StorePath
from kmd.model.preconditions_model import Precondition
from kmd.exec.combiners import Combiner, combine_as_paragraphs
from kmd.text_ui.command_output import output_separator
from kmd.util.type_utils import not_none

log = get_logger(__name__)


def look_up_actions(action_names: List[str]) -> List[Action]:
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
        look_up_actions(self.action_names)  # Validate action names.

        log.message("%s Begin action sequence `%s`", EMOJI_ACTION, self.name)

        original_input_paths = [not_none(item.store_path) for item in items]
        transient_outputs: List[Item] = []

        for i, action_name in enumerate(self.action_names):
            for item in items:
                if not item.store_path:
                    raise InvalidInput("Item must have a store path: %s", item)

            output_separator()
            log.message(
                "%s Action sequence `%s`: Part %s of %s: `%s`",
                EMOJI_ACTION,
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

        # The final items should be derived from the original inputs.
        for item in items:
            item.update_relations(derived_from=original_input_paths)

        log.message("Action sequence `%s` complete. Archiving transient items.", self.name)
        ws = current_workspace()
        for item in transient_outputs:
            assert item.store_path
            ws.archive(StorePath(item.store_path))

        output_separator()

        return ActionResult(items)


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
        look_up_actions(self.action_names)  # Validate action names.

        for item in items:
            if not item.store_path:
                raise InvalidInput("Item must have a store path: %s", item)

        item_paths = [not_none(item.store_path) for item in items]

        results: List[ActionResult] = []

        for i, action_name in enumerate(self.action_names):
            output_separator()
            log.message(
                "%s Action combo `%s`: Part %s of %s: %s",
                EMOJI_ACTION,
                self.name,
                i + 1,
                len(self.action_names),
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