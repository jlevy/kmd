from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole
from kmd.help.assistant import assistant_preamble
from kmd.llms.fuzzy_parsing import strip_markdown_fence
from kmd.llms.llm_completion import llm_completion
from kmd.model import (
    ActionInput,
    ActionResult,
    ArgCount,
    Format,
    ItemType,
    LLMAction,
    Message,
    MessageTemplate,
    Precondition,
    TitleTemplate,
)
from kmd.model.actions_model import ONE_ARG
from kmd.model.language_models import LLM
from kmd.model.model_settings import DEFAULT_CAREFUL_LLM
from kmd.preconditions.precondition_defs import is_instructions
from kmd.util.type_utils import not_none

log = get_logger(__name__)


@kmd_action
class WriteNewAction(LLMAction):

    name: str = "write_new_action"

    description: str = (
        """
        Create a new kmd action in Python, based on a description of the features.
        Write an instruction to give as input.
        """
    )

    cachable: bool = False

    model: LLM = LLM.o1_preview

    title_template: TitleTemplate = TitleTemplate("Action: {title}")

    template: MessageTemplate = MessageTemplate(
        """
        Write a kmd action according to the following description. Guidelines:

        - Only provide the Python code verbatim. DO NOT offer any explanatory text,
            around the code. Put these within comments!
        
        - Do not include Markdown formatting or ``` code blocks.

        - If desired behavior of the code is not clear from the description, add
            comment placeholders in the code so it can be filled in later.

        - Subclass Action or in most cases, a subclass of it like CachedItemAction
            or CachedLLMAction (these two actions are the most common ones, and operate
            on one item at a time).
.
        To illustrate, here is an example of the correct format for an action that
        strips HTML tags:

        from kmd.config.logger import get_logger
        from kmd.errors import InvalidInput
        from kmd.exec.action_registry import kmd_action
        from kmd.model import Format, Item, ItemType, PerItemAction, Precondition
        from kmd.preconditions.precondition_defs import has_html_body, has_text_body
        from kmd.util.format_utils import html_to_plaintext

        log = get_logger(__name__)


        @kmd_action
        class StripHtml(PerItemAction):

            name: str = "strip_html"

            description: str = "Strip HTML tags from HTML or Markdown."

            precondition: Precondition = has_html_body | has_text_body

            def run_item(self, item: Item) -> Item:
                if not item.body:
                    raise InvalidInput("Item must have a body")

                clean_body = html_to_plaintext(item.body)
                output_item = item.derived_copy(
                    type=ItemType.doc,
                    format=Format.markdown,
                    body=clean_body,
                )

                return output_item

        Action description:

        {body}

        Action implementation in Python:
        # action_implementation.py:
        
        """
    )

    expected_args: ArgCount = ONE_ARG

    precondition: Precondition = is_instructions

    def run(self, items: ActionInput) -> ActionResult:
        instructions_item = items[0]
        instructions = ChatHistory.from_yaml(not_none(instructions_item.body))

        # Give the LLM full context on kmd APIs.
        # But we do this here lazily to prevent circular dependencies.
        system_message = Message(assistant_preamble(skip_api=False, base_only=False))
        instructions.messages.insert(0, ChatMessage(ChatRole.system, system_message))

        model = self.model or DEFAULT_CAREFUL_LLM
        llm_response = llm_completion(
            model,
            messages=instructions.as_chat_completion(),
        )
        python_body = strip_markdown_fence(llm_response)
        if python_body != llm_response:
            log.message(
                "Stripped extraneous Markdown, keeping %s of %s chars",
                len(python_body),
                len(llm_response),
            )
        result_item = instructions_item.derived_copy(
            type=ItemType.extension, format=Format.python, body=python_body
        )

        return ActionResult([result_item])
