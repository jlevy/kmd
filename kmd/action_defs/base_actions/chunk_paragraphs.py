from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    CachedTextAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.precondition_defs.common_preconditions import is_markdown
from kmd.text_docs.div_chunks import chunk_paras_into_divs
from kmd.text_docs.sizes import TextUnit

log = get_logger(__name__)


@kmd_action
class ChunkParagraphs(CachedTextAction):
    def __init__(self):
        super().__init__(
            name="chunk_paragraphs",
            description="Group paragraphs into chunks, demarcated by div tags.",
            expected_args=ONE_OR_MORE_ARGS,
            precondition=is_markdown,
            chunk_size=200,
            chunk_unit=TextUnit.WORDS,
        )

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput(f"Item must have a body: {item}")
        if self.chunk_size is None or self.chunk_unit is None:
            raise InvalidInput(
                f"Chunk size and unit must be set: {self.chunk_size}, {self.chunk_unit}"
            )

        clean_body = chunk_paras_into_divs(item.body, self.chunk_size, self.chunk_unit)

        output_item = item.derived_copy(
            type=ItemType.note,
            format=Format.markdown,
            body=clean_body,
        )

        return output_item
