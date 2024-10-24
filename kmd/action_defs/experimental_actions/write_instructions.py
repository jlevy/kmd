from kmd.exec.action_registry import kmd_action
from kmd.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.model import Action, ActionInput, ActionResult, ArgCount, Format, Item, ItemType, NO_ARGS


@kmd_action
class WriteInstructions(Action):

    name: str = "write_instructions"

    description: str = "Write a chat item with system and user instructions."

    expected_args: ArgCount = NO_ARGS

    interactive_input: bool = True

    cacheable: bool = False

    def run(self, items: ActionInput) -> ActionResult:
        chat_history = ChatHistory()

        system_instructions = prompt_simple_string(
            "Enter the system instructions (or enter for none): "
        )
        system_instructions = system_instructions.strip()
        if system_instructions:
            chat_history.append(ChatMessage(ChatRole.system, system_instructions))

        user_instructions = prompt_simple_string("Enter the user instructions: ")
        user_instructions = user_instructions.strip()
        if user_instructions:
            chat_history.append(ChatMessage(ChatRole.user, user_instructions))

        if chat_history.messages:
            item = Item(
                ItemType.chat,
                body=chat_history.to_yaml(),
                format=Format.yaml,
            )

            return ActionResult([item])
        else:
            return ActionResult([])
