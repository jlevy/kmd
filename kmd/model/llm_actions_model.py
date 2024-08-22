from dataclasses import dataclass
from typing import Optional
from kmd.config.logger import get_logger
from kmd.config.settings import DEFAULT_CAREFUL_MODEL
from kmd.exec.llm_transforms import llm_transform_item, llm_transform_str
from kmd.model.actions_model import (
    ActionInput,
    ActionResult,
    CachedItemAction,
    TransformAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.html_conventions import CHUNK, RESULT
from kmd.model.items_model import UNTITLED, Format, Item
from kmd.model.language_models import LLM
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_defs import has_div_chunks
from kmd.text_chunks.div_chunks import div, insert_chunk_child
from kmd.text_chunks.parse_divs import parse_divs_by_class, TextNode


log = get_logger(__name__)


@dataclass(frozen=True)
class CachedLLMAction(TransformAction, CachedItemAction):
    """
    Base LLM action that processes each item and is cached.
    """

    model: Optional[LLM] = DEFAULT_CAREFUL_MODEL

    def run(self, items: ActionInput) -> ActionResult:
        return super(CachedItemAction, self).run(items)

    def run_item(self, item: Item) -> Item:
        """
        Override to customize item handling.
        """
        return llm_transform_item(self, item)


@dataclass(frozen=True)
class ChunkedLLMAction(CachedLLMAction):
    """
    Base class for LLM actions that operate on chunks that are already marked with divs.
    """

    precondition: Optional[Precondition] = has_div_chunks
    chunk_class: str = CHUNK

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput(f"LLM actions expect a body: {self.name} on {item}")

        output = []
        for chunk in parse_divs_by_class(item.body, self.chunk_class):
            output.append(self.process_chunk(chunk))

        result_item = item.derived_copy(body="\n\n".join(output), format=Format.md_html)

        if self.title_template:
            result_item.title = self.title_template.format(
                title=(item.title or UNTITLED), action_name=self.name
            )

        return result_item

    def process_chunk(self, chunk: TextNode) -> str:
        """
        Override to customize chunk handling.
        """
        llm_response = llm_transform_str(self, chunk.contents)
        new_div = div(RESULT, llm_response)

        return insert_chunk_child(chunk, new_div)
