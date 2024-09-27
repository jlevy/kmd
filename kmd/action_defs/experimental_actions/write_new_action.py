from kmd.exec.action_registry import kmd_action
from kmd.exec.llm_transforms import llm_transform_item
from kmd.file_storage.workspaces import current_workspace
from kmd.help.assistant import assistant_preamble
from kmd.model import (
    ActionInput,
    ActionResult,
    Format,
    ItemType,
    LLMAction,
    Message,
    MessageTemplate,
    TitleTemplate,
)
from kmd.model.actions_model import ONE_ARG
from kmd.model.language_models import LLM
from kmd.preconditions.precondition_defs import is_instruction


@kmd_action
class WriteNewAction(LLMAction):
    def __init__(self):
        super().__init__(
            name="write_new_action",
            description="""
            Create a new kmd action in Python, based on a description of the features.
            Write an instruction to give as input.
            """,
            model=LLM.o1_preview,
            system_message=None,  # Will set this in run().
            title_template=TitleTemplate("Action: {title}"),
            template=MessageTemplate(
                """
                Write a kmd action according to the following description. Guidelines:

                - Output ONLY the Python code required, without any explanatory text, except for
                specific and brief comments in the code.
                
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
                from kmd.exec.action_registry import kmd_action
                from kmd.model import CachedDocAction, Format, InvalidInput, Item, ItemType
                from kmd.preconditions.precondition_defs import has_html_body, has_text_body
                from kmd.text_formatting.text_formatting import html_to_plaintext

                log = get_logger(__name__)


                @kmd_action
                class StripHtml(CachedDocAction):
                    def __init__(self):
                        super().__init__(
                            name="strip_html",
                            description="Strip HTML tags from HTML or Markdown.",
                            precondition=has_html_body | has_text_body,
                        )

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
            ),
            expected_args=ONE_ARG,
            precondition=is_instruction,
        )

    def run(self, items: ActionInput) -> ActionResult:
        # Give the LLM full context on kmd APIs.
        # But we do this here lazily to prevent circular dependencies.
        self.system_message = Message(assistant_preamble(skip_api=False, base_only=False))

        description_item = items[0]

        workspace = current_workspace()
        workspace.save(description_item)

        result_item = llm_transform_item(self, description_item)
        result_item.type = ItemType.extension
        result_item.format = Format.python

        return ActionResult([result_item])
