from textwrap import dedent
from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import (
    CachedItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import has_div_chunks, is_readable_text
from kmd.text_chunks.div_chunks import chunk_text_into_divs
from kmd.text_docs.sizes import TextUnit

log = get_logger(__name__)


@kmd_action
class Chunkify(CachedItemAction):
    def __init__(self):
        super().__init__(
            name="chunkify",
            description=dedent(
                """
                Group paragraphs or top-level divs into chunks, demarcated by <div class="chunk"> tags.
                If desired, set `chunk_size` to a large value, to indicate that the entire document
                should be processed as one chunk.
                """
            ),
            # Don't chunkify if already chunkified.
            precondition=is_readable_text & ~has_div_chunks,
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

        chunked_body = chunk_text_into_divs(item.body, self.chunk_size, self.chunk_unit)

        output_item = item.derived_copy(
            type=ItemType.note,
            format=Format.markdown,
            body=chunked_body,
        )

        return output_item
