from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import CachedItemAction
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import is_markdown_list
from kmd.text_formatting.markdown_normalization import normalize_concepts_list

log = get_logger(__name__)


@kmd_action()
class NormalizeConcepts(CachedItemAction):
    def __init__(self):
        super().__init__(
            name="normalize_concepts",
            description="Normalize, capitalize, sort, and remove duplicates from a Markdown list of concepts.",
            precondition=is_markdown_list,
        )

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput("Item must have a body")

        body = normalize_concepts_list(item.body)

        output_item = item.derived_copy(
            type=ItemType.note,
            format=Format.markdown,
            body=body,
        )

        return output_item
