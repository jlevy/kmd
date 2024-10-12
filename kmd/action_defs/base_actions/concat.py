from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import (
    Action,
    ActionInput,
    ActionResult,
    ArgCount,
    Item,
    ItemType,
    ONE_OR_MORE_ARGS,
    Param,
    ParamList,
    Precondition,
    TitleTemplate,
    UNTITLED,
)
from kmd.preconditions.precondition_defs import has_text_body
from kmd.util.type_utils import not_none

log = get_logger(__name__)


@kmd_action
class Concat(Action):

    name: str = "concat"

    description: str = (
        "Concatenate the given text documents into a single document. Adds titles to each section."
    )

    expected_args: ArgCount = ONE_OR_MORE_ARGS

    precondition: Precondition = has_text_body

    params: ParamList = (
        Param("separator", "Separator string.", default_value="\n\n", type=str),
        Param("section_template", "Title template.", default_value="## {title}", type=str),
    )

    separator: str = "\n\n"

    section_template: str = "## {title}"

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
