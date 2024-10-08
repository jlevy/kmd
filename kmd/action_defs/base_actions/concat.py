from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import (
    Action,
    ActionInput,
    ActionResult,
    Item,
    ItemType,
    ONE_OR_MORE_ARGS,
    TitleTemplate,
    UNTITLED,
)
from kmd.preconditions.precondition_defs import has_text_body
from kmd.util.type_utils import not_none

log = get_logger(__name__)


@kmd_action
class Concat(Action):
    separator = "\n\n"
    section_template = "## {title}"

    def __init__(self):
        super().__init__(
            name="concat",
            description="Concatenate the given text documents into a single document. Adds titles to each section.",
            precondition=has_text_body,
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run(self, items: ActionInput) -> ActionResult:
        def titled_body(item: Item) -> str:
            return (
                TitleTemplate(self.section_template).format(title=item.title or UNTITLED)
                + self.separator
                + not_none(item.body)
            )

        concatenated_text = self.separator.join(titled_body(item) for item in items if item.body)

        result_item = items[0].derived_copy(
            type=ItemType.doc,
            body=concatenated_text,
        )

        return ActionResult([result_item])
