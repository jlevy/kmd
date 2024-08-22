from textwrap import dedent
from kmd.exec.action_registry import kmd_action
from kmd.exec.llm_transforms import llm_transform_item
from kmd.help.assistant import assistant_preamble
from kmd.file_storage.workspaces import current_workspace
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.model.actions_model import (
    ONE_OR_NO_ARGS,
    ActionInput,
    ActionResult,
    LLMMessage,
    LLMTemplate,
    TitleTemplate,
)
from kmd.model.items_model import Format, Item, ItemType
from kmd.model.actions_model import TransformAction
from kmd.util.lazyobject import lazyobject


@lazyobject
def assistant_coding_preamble() -> LLMMessage:
    return LLMMessage(assistant_preamble(False, False))


@kmd_action
class WriteNewAction(TransformAction):
    def __init__(self):
        super().__init__(
            name="write_new_action",
            description="Create a new kmd action in Python, based on a description of the features.",
            system_message=assistant_coding_preamble,  # Give it context on kmd APIs.
            title_template=TitleTemplate("Action: {title}"),
            template=LLMTemplate(
                dedent(
                    """
                    Write a kmd action according to the following description. Guidelines:

                    - Output ONLY the Python code required, without any explanatory text, except for
                    specific and brief comments in the code.
                    
                    - Do not include Markdown formatting or ``` code blocks.

                    - If desired behavior of the code is not clear from the description, add
                    comment placeholders in the code so it can be filled in later.

                    - Subclass Action or EachItemAction (if the input and output are one item).

                    To illustrate, here is an example of the correct format for an action that
                    strips HTML tags:

                        from kmd.action_exec.action_registry import kmd_action
                        from kmd.model.actions_model import (
                            ONE_OR_MORE_ARGS,
                            EachItemAction,
                        )
                        from kmd.model.errors_model import InvalidInput
                        from kmd.model.items_model import Format, Item, ItemType
                        from kmd.config.logger import get_logger
                        from kmd.text_docs.wordtoks import raw_text_to_wordtoks, visualize_wordtoks
                        from kmd.text_formatting.text_formatting import html_to_plaintext


                        @kmd_action
                        class StripHtml(EachItemAction):
                            def __init__(self):
                                super().__init__(
                                    name="strip_html",
                                    description="Strip HTML tags from text or Markdown.",
                                )

                            def run_item(self, item: Item) -> Item:
                                if not item.body:
                                    raise InvalidInput(f"Item must have a body")

                                clean_body = html_to_plaintext(item.body)
                                new_title = item.title + " (clean text)"
                                output_item = item.derived_copy(
                                    type=ItemType.note, title=new_title, body=clean_body, format=Format.markdown
                                )

                                return output_item

                    Action description:

                    {body}

                    Action implementation in Python:
                    # action_implementation.py:
                    
                    """
                )
            ),
            expected_args=ONE_OR_NO_ARGS,
            interactive_input=True,
        )

    def run(self, items: ActionInput) -> ActionResult:
        # If the instructions are selected as the one input, use them.
        if len(items) == 1 and items[0].type == ItemType.instruction:
            description_item = items[0]
        else:
            # Otherwise, let's prompt for them.
            action_description = prompt_simple_string(
                "Enter a description of the Action you want to build: "
            )
            description_item = Item(
                ItemType.instruction,
                body=action_description,
                format=Format.markdown,
            )

        workspace = current_workspace()
        workspace.save(description_item)

        result_item = llm_transform_item(self, description_item)
        result_item.type = ItemType.extension
        result_item.format = Format.python

        return ActionResult([result_item])
