from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import (
    CachedItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import is_readable_text
from kmd.text_chunks.div_chunks import chunk_paras_into_divs
from kmd.text_docs.sizes import TextUnit

log = get_logger(__name__)


@kmd_action
class ChunkParagraphs(CachedItemAction):
    def __init__(self):
        super().__init__(
            name="chunk_paragraphs",
            description="Group paragraphs into chunks, demarcated by div tags.",
            precondition=is_readable_text,
            chunk_size=2000,
            chunk_unit=TextUnit.words,
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
