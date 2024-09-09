from textwrap import dedent

from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import CachedDocAction, Format, InvalidInput, Item, ItemType
from kmd.preconditions.precondition_defs import has_div_chunks, is_text_doc
from kmd.text_chunks.div_elements import chunk_text_as_divs
from kmd.text_docs.sizes import TextUnit

log = get_logger(__name__)


@kmd_action()
class Chunkify(CachedDocAction):
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
            precondition=is_text_doc & ~has_div_chunks,
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

        chunked_body = chunk_text_as_divs(item.body, self.chunk_size, self.chunk_unit)

        output_item = item.derived_copy(
            type=ItemType.doc,
            format=Format.markdown,
            body=chunked_body,
        )

        return output_item
