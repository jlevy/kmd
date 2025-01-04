from kmd.config.logger import get_logger
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
    ONE_OR_NO_ARGS,
    ParamList,
    Precondition,
    ShellResult,
)
from kmd.preconditions.precondition_defs import is_chat
from kmd.shell_ui.shell_output import print_assistance, print_response, print_style, Style, Wrap


log = get_logger(__name__)


@kmd_action
class Chat(Action):

    name: str = "chat"

    description: str = """
        Chat with an LLM. By default, starts a new chat session. If provided a chat
        history item, will continue an existing chat.
        """

    expected_args: ArgCount = ONE_OR_NO_ARGS

    uses_selection: bool = False

    interactive_input: bool = True

    cacheable: bool = False

    params: ParamList = common_params("model")

    precondition: Precondition = is_chat

    model: LLM = DEFAULT_CAREFUL_LLM

    def run(self, items: ActionInput) -> ActionResult:
        if items:
            chat_history = ChatHistory.from_item(items[0])
            size_desc = f"{chat_history.size_summary()} in chat history"
        else:
            chat_history = ChatHistory()
            size_desc = "empty chat history"

        print_response(
            f"Beginning chat with {size_desc}. Press enter (or type `exit`) to end chat.",
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

            chat_history.append(ChatMessage(ChatRole.user, user_message))

            llm_response = llm_completion(
                self.model,
                messages=chat_history.as_chat_completion(),
            )

            with print_style(Style.PAD):
                print_assistance("%s", llm_response.content)

            # TODO: Why does the response have trailing whitespace on lines? Makes the YAML ugly.
            stripped_response = "\n".join(
                line.rstrip() for line in llm_response.content.splitlines()
            )

            chat_history.append(ChatMessage(ChatRole.assistant, stripped_response))

        if chat_history.messages:
            item = Item(
                ItemType.chat,
                body=chat_history.to_yaml(),
                format=Format.yaml,
            )

            return ActionResult([item])
        else:
            log.warning("Empty chat! Not saving anything.")
            return ActionResult([], shell_result=ShellResult(show_selection=False))
