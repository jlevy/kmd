import html

import regex
from kmd.actions.action_registry import register_action
from kmd.file_storage.workspaces import current_workspace
from kmd.model.actions_model import ONE_OR_MORE_ARGS, Action, ActionInput, ActionResult
from kmd.model.items_model import ItemType
from kmd.config.logger import get_logger
from kmd.text_handling.text_formatting import html_to_plaintext

log = get_logger(__name__)


@register_action
class StripHtml(Action):
    def __init__(self):
        super().__init__(
            name="strip_html",
            friendly_name="Strip HTML Tags",
            description="Strip HTML tags from text or Markdown.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        if not item.body:
            raise ValueError(f"Item must have a body: {item}")

        clean_body = html_to_plaintext(item.body)
        new_title = f"{item.title} (clean text)"
        output_item = item.new_copy_with(type=ItemType.note, title=new_title, body=clean_body)

        current_workspace().save(output_item)
        return ActionResult([output_item])