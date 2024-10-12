from kmd.exec.action_registry import kmd_action
from kmd.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.llms.llm_completion import llm_completion
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
    NO_ARGS,
    ParamList,
)
from kmd.text_ui.command_output import output_assistance, output_response


@kmd_action
class Chat(Action):

    name: str = "chat"

    description: str = "Chat with an LLM."

    expected_args: ArgCount = NO_ARGS

    interactive_input: bool = True

    cachable: bool = False

    params: ParamList = common_params("model")

    model: LLM = DEFAULT_CAREFUL_LLM

    def run(self, items: ActionInput) -> ActionResult:
        chat_history = ChatHistory()

        output_response("Beginning chat. Press enter (or type `exit`) to end chat.")

        while True:
            try:
                user_message = prompt_simple_string(self.model.value)
            except (KeyboardInterrupt, EOFError):
                break

            user_message = user_message.strip()
            if not user_message or user_message.lower() == "exit" or user_message.lower() == "quit":
                break

            chat_history.append(ChatMessage(ChatRole.user, user_message))

            llm_response = llm_completion(
                self.model,
                messages=chat_history.as_chat_completion(),
            )

            output_assistance("%s", llm_response)

            # TODO: Why does the response have trailing whitespace on lines? Makes the YAML ugly.
            stripped_response = "\n".join(line.rstrip() for line in llm_response.splitlines())

            chat_history.append(ChatMessage(ChatRole.assistant, stripped_response))

        if chat_history.messages:
            item = Item(
                ItemType.chat,
                body=chat_history.to_yaml(),
                format=Format.yaml,
            )

            return ActionResult([item])
        else:
            return ActionResult([])
