from kmd.exec.action_registry import kmd_action
from kmd.llms.fuzzy_parsing import strip_markdown_fence
from kmd.model import Item, PerItemAction, Precondition
from kmd.preconditions.precondition_defs import contains_fenced_code


@kmd_action
class StripMarkdownFence(PerItemAction):

    name: str = "strip_markdown_fence"

    description: str = """
        If code content is included in a Markdown fence, strip the extraneous Markdown
        and return only the first fenced code block.
        """

    precondition: Precondition = contains_fenced_code

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise ValueError("Item has no body")

        new_body = strip_markdown_fence(item.body)
        return item.derived_copy(
            type=item.type,
            body=new_body,
        )
