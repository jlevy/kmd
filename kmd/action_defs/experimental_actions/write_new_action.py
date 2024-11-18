from typing import Optional

from kmd.config.logger import get_logger
from kmd.errors import ApiResultError
from kmd.exec.action_exec import run_action
from kmd.exec.action_registry import kmd_action
from kmd.exec.system_actions import write_instructions
from kmd.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole
from kmd.help.assistant import assist_preamble, structured_assistance
from kmd.model import (
    Action,
    ActionInput,
    ActionResult,
    ArgCount,
    DEFAULT_CAREFUL_LLM,
    Format,
    ItemType,
    LLM,
    Message,
    ONE_OR_NO_ARGS,
    Precondition,
    TitleTemplate,
)
from kmd.preconditions.precondition_defs import is_instructions
from kmd.shell.assistant_output import print_assistant_response
from kmd.shell.shell_output import fill_text, Wrap
from kmd.util.lazyobject import lazyobject
from kmd.util.type_utils import not_none

log = get_logger(__name__)


@lazyobject
def write_action_instructions() -> str:
    from kmd.docs.assemble_source_code import load_source_code

    return (
        """
        Write a kmd action according to the following description. Guidelines:

        - Provide Python code in the python_code field.
        
        - Add non-code commentary in the response_text field.

        - If desired behavior of the code is not clear from the description, add
            comment placeholders in the code so it can be filled in later.

        - Look at the example below. Commonly, you will subclass PerItemAction
          for simple actions that work on one item at a time. Subclass LLMAction
          if it is simply a transformation of the input using an LLM.
.
        To illustrate, here are a cuople examples of the correct format for an action that
        strips HTML tags:
        """
        + load_source_code().example_action_src.replace("{", "{{").replace("}", "}}")
        + """
        
        I'll give you a description of an action and possibly more refinements
        and you will write the Python code for the action.
        """
    )


@kmd_action
class WriteNewAction(Action):

    name: str = "write_new_action"

    description: str = (
        """
        Create a new kmd action in Python, based on a description of the features.
        If no input is provided, will start an interactive chat to collect the action description.
        """
    )

    cacheable: bool = False

    model: LLM = LLM.gpt_4o
    # model: LLM = LLM.o1_preview  # Structured outputs not working here?

    title_template: TitleTemplate = TitleTemplate("Action: {title}")

    expected_args: ArgCount = ONE_OR_NO_ARGS

    interactive_input: bool = True

    precondition: Precondition = is_instructions

    @property
    def formatted_description(self) -> Optional[str]:
        if not self.description:
            return None
        else:
            return fill_text(self.description, text_wrap=Wrap.WRAP_FULL, extra_indent="# ")

    def run(self, items: ActionInput) -> ActionResult:
        if not items:
            # Start a chat to collect the action description.
            # TODO: Consider generalizing this so an action can declare an input action to collect its input.
            chat_result = run_action(write_instructions, internal_call=True)
            if not chat_result.items:
                raise ApiResultError("No chat input provided")

            action_description_item = chat_result.items[0]
        else:
            action_description_item = items[0]

        # Manually check precondition since we might have created the item
        self.precondition.check(action_description_item, f"action `{self.name}`")

        chat_history = ChatHistory()

        # Give the LLM full context on kmd APIs.
        # But we do this here lazily to prevent circular dependencies.
        system_message = Message(assist_preamble(skip_api=False, base_actions_only=False))
        chat_history.extend(
            [
                ChatMessage(ChatRole.system, system_message),
                ChatMessage(ChatRole.user, str(write_action_instructions)),
                *ChatHistory.from_yaml(not_none(action_description_item.body)).messages,
            ]
        )

        model = self.model or DEFAULT_CAREFUL_LLM
        assistant_response = structured_assistance(chat_history.as_chat_completion(), model)

        print_assistant_response(assistant_response, model)

        if not assistant_response.python_code:
            raise ApiResultError("No Python code provided in the response.")

        body = assistant_response.python_code
        commented_body = "\n\n".join(filter(None, [self.formatted_description, body]))

        result_item = action_description_item.derived_copy(
            type=ItemType.extension,
            format=Format.python,
            title=self.title_template.format(title=action_description_item.title),
            body=commented_body,
        )

        return ActionResult([result_item])
