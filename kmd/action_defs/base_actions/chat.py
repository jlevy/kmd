from kmd.exec.action_registry import kmd_action
from kmd.file_formats.chat_format import ChatHistory, ChatMessage, ChatType
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.llms.llm_completion import llm_completion
from kmd.model import Action, ActionInput, ActionResult, Format, Item, ItemType, NO_ARGS
from kmd.model.model_settings import DEFAULT_CAREFUL_LLM
from kmd.text_ui.command_output import output_assistance, output_response


@kmd_action
class Chat(Action):
    def __init__(self):
        super().__init__(
            name="chat",
            description="Chat with an LLM.",
            expected_args=NO_ARGS,
            interactive_input=True,
            cachable=False,
        )

    def run(self, items: ActionInput) -> ActionResult:
        chat_history = ChatHistory()
        model = self.model or DEFAULT_CAREFUL_LLM

        output_response("Beginning chat. Press enter (or type `exit`) to end chat.")

        while True:
            try:
                user_message = prompt_simple_string(model.value)
            except (KeyboardInterrupt, EOFError):
                break

            user_message = user_message.strip()
            if not user_message or user_message.lower() == "exit" or user_message.lower() == "quit":
                break

            chat_history.append(ChatMessage(ChatType.user, user_message))

            llm_response = llm_completion(
                model,
                messages=chat_history.as_chat_completion(),
            )

            output_assistance("%s", llm_response)

            # TODO: Why does the response have trailing whitespace on lines? Makes the YAML ugly.
            stripped_response = "\n".join(line.rstrip() for line in llm_response.splitlines())

            chat_history.append(ChatMessage(ChatType.assistant, stripped_response))

        if chat_history.messages:
            item = Item(
                ItemType.chat,
                body=chat_history.to_yaml(),
                format=Format.yaml,
            )

            return ActionResult([item])
        else:
            return ActionResult([])
