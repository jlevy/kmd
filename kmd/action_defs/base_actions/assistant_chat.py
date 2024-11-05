from kmd.exec.action_registry import kmd_action
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.help.assistant import assistance, assistant_chat_history
from kmd.model import (
    Action,
    ActionInput,
    ActionResult,
    ArgCount,
    common_params,
    DEFAULT_CAREFUL_LLM,
    Format,
    Item,
    ItemType,
    LLM,
    ParamList,
)
from kmd.model.args_model import NO_ARGS
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_defs import is_chat
from kmd.shell.shell_output import print_response, Wrap


@kmd_action
class AssistantChat(Action):

    name: str = "assistant_chat"

    description: str = "Chat with the Kmd assistant."

    expected_args: ArgCount = NO_ARGS

    interactive_input: bool = True

    cacheable: bool = False

    params: ParamList = common_params("model")

    precondition: Precondition = is_chat

    model: LLM = DEFAULT_CAREFUL_LLM

    def run(self, items: ActionInput) -> ActionResult:
        chat_history = assistant_chat_history(include_system_message=True, fast=False)
        print_response(
            f"Beginning chat the assistant with history of {chat_history.size_summary()}."
            " Press enter (or type `exit`) to end chat.",
            text_wrap=Wrap.WRAP_FULL,
        )

        while True:
            try:
                user_message = prompt_simple_string(self.model.value)
            except KeyboardInterrupt:
                break

            user_message = user_message.strip()
            if not user_message or user_message.lower() == "exit" or user_message.lower() == "quit":
                break

            assistance(user_message)

        if chat_history.messages:
            item = Item(
                ItemType.chat,
                body=chat_history.to_yaml(),
                format=Format.yaml,
            )

            return ActionResult([item])
        else:
            return ActionResult([])
