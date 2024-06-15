from typing import Optional
from kmd.action_exec.action_exec import run_action
from kmd.action_exec.action_registry import kmd_action
from kmd.action_exec.llm_action_base import LLMAction
from kmd.config.text_styles import EMOJI_PROCESS
from kmd.model.actions_model import Action, ActionInput, ActionResult
from kmd.config.logger import get_logger
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
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

    extra_desc = "This action is a sequence of these actions: " + ", ".join(action_names) + "."
    full_description = " ".join([description, extra_desc]) if description else extra_desc

    @kmd_action
    class SequenceAction(Action):
        def __init__(self):
            super().__init__(
                name=name, friendly_name=friendly_name or name, description=full_description
            )

            self.action_sequence = action_names

        def run(self, items: ActionInput) -> ActionResult:
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


# def define_action_combo(
#     name,
#     *action_names: str,
#     separator="\n\n",
#     friendly_name: Optional[str] = None,
#     description: Optional[str] = None,
# ) -> None:
#     """
#     Register an action that combines the results of other actions.
#     """

#     if not action_names or len(action_names) <= 1:
#         raise InvalidInput("Action must have at least two sub-actions: %s", action_names)

#     extra_desc = "This action combines outputs of these actions: " + ", ".join(action_names) + "."
#     full_description = " ".join([description, extra_desc]) if description else extra_desc

#     @kmd_action
#     class ComboAction(Action):
#         def __init__(self):
#             super().__init__(
#                 name=name, friendly_name=friendly_name or name, description=full_description
#             )
#             self.action_sequence = action_names
#             self.separator = separator

#         def run(self, items: ActionInput) -> ActionResult:
#             results = []
#             for action_name in self.action_sequence:
#                 action = look_up_action(action_name)
#                 result = action.run(items)
#                 for item in result.items:
#                     results.append(item.body)

#             combined_result = self.separator.join(results)

#             result_title = f"{self.friendly_name} of {items[0].title}"
#             if len(items) > 1:
#                 result_title += f" and {len(items) - 1} other items"

#             result_item = Item(
#                 title=result_title,
#                 body=combined_result,
#                 type=ItemType.note,
#                 format=Format.markdown,
#             )
#             return ActionResult([result_item])
