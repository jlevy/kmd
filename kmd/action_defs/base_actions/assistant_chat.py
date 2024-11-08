from kmd.exec.action_registry import kmd_action
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.help.assistant import assistant_chat_history, shell_context_assistance
from kmd.model import (
    Action,
    ActionInput,
    ActionResult,
    ArgCount,
    common_params,
    DEFAULT_CAREFUL_LLM,
    LLM,
    ParamList,
)
from kmd.model.args_model import NO_ARGS
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_defs import is_chat
from kmd.shell.assistant_output import print_assistant_heading
from kmd.shell.shell_output import cprint, print_response, Wrap


@kmd_action
class AssistantChat(Action):

    name: str = "assistant_chat"

    description: str = """
        Chat with the Kmd assistant. This is just the same as typing on the command line,
        but with a chat session.
        """

    expected_args: ArgCount = NO_ARGS

    interactive_input: bool = True

    cacheable: bool = False

    params: ParamList = common_params("model")

    precondition: Precondition = is_chat

    model: LLM = DEFAULT_CAREFUL_LLM

    def run(self, items: ActionInput) -> ActionResult:
        chat_history = assistant_chat_history(include_system_message=True, fast=False)
        cprint()
        print_assistant_heading(self.model)
        print_response(
            f"History of {chat_history.size_summary()}.\n"
            "Press enter (or type `exit`) to end chat.",
            text_wrap=Wrap.NONE,
        )

        while True:
            try:
                user_message = prompt_simple_string(f"assistant/{self.model.value}")
            except KeyboardInterrupt:
                break

            user_message = user_message.strip()
            if not user_message or user_message.lower() == "exit" or user_message.lower() == "quit":
                break

            shell_context_assistance(user_message, silent=True, model=self.model)

        return ActionResult([])
