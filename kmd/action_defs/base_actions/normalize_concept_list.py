from kmd.concepts.concept_formats import concepts_from_markdown
from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.model import Format, Item, ItemType, PerItemAction, Precondition
from kmd.preconditions.precondition_defs import is_markdown_list
from kmd.text_formatting.markdown_util import as_bullet_points

log = get_logger(__name__)


@kmd_action
class NormalizeConceptList(PerItemAction):

    name: str = "normalize_concept_list"

    description: str = """
        Normalize, capitalize, sort, and remove duplicates from a Markdown list of concepts.
        """

    precondition: Precondition = is_markdown_list

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput("Item must have a body")

        body = as_bullet_points(concepts_from_markdown(item.body))

        output_item = item.derived_copy(
            type=ItemType.doc,
            format=Format.markdown,
            body=body,
        )

        return output_item
