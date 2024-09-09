from kmd.exec.action_registry import kmd_action
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.model import (
    NO_ARGS,
    Action,
    ActionInput,
    ActionResult,
)
from kmd.model import Format
from kmd.model import Item, ItemType


@kmd_action()
class WriteInstructions(Action):
    def __init__(self):
        super().__init__(
            name="write_instructions",
            description="Write an item with instructions (e.g. for an LLM action that accepts instructions).",
            expected_args=NO_ARGS,
            interactive_input=True,
        )

    def run(self, items: ActionInput) -> ActionResult:
        # Prompt for instructions.
        instructions = prompt_simple_string("Enter the instructions you want to save: ")
        item = Item(
            ItemType.instruction,
            body=instructions,
            format=Format.markdown,
        )

        return ActionResult([item])
