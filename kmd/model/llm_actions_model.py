from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.model.actions_model import (
    ActionInput,
    ActionResult,
    CachedDocAction,
    ForEachItemAction,
    TransformAction,
)
from kmd.model.doc_elements import CHUNK, ORIGINAL, RESULT
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, UNTITLED
from kmd.model.language_models import LLM
from kmd.model.model_settings import DEFAULT_CAREFUL_LLM
from kmd.model.preconditions_model import Precondition
from kmd.util.task_stack import task_stack

if TYPE_CHECKING:
    from kmd.text_chunks.text_node import TextNode

log = get_logger(__name__)


@dataclass(frozen=True)
class LLMAction(TransformAction, ForEachItemAction):
    """
    Base LLM action that processes each item and is cached.
    """

    model: Optional[LLM] = DEFAULT_CAREFUL_LLM

    def run(self, items: ActionInput) -> ActionResult:
        return super(ForEachItemAction, self).run(items)

    def run_item(self, item: Item) -> Item:
        """
        Override to customize item handling.
        """
        from kmd.exec.llm_transforms import llm_transform_item
        from kmd.text_formatting.markdown_normalization import normalize_markdown

        item = llm_transform_item(self, item)
        if item.body:
            item.body = normalize_markdown(item.body)
        return item


@dataclass(frozen=True)
class CachedLLMAction(LLMAction, CachedDocAction):
    """
    Base LLM action that processes each item and is cached.
    """

    def run(self, items: ActionInput) -> ActionResult:
        return super(CachedDocAction, self).run(items)


@dataclass(frozen=True)
class ChunkedLLMAction(CachedLLMAction):
    """
    Base class for LLM actions that operate on chunks that are already marked with divs.
    """

    precondition: Optional[Precondition] = None
    chunk_class: str = CHUNK

    def __post_init__(self):
        from kmd.preconditions.precondition_defs import has_div_chunks

        if not self.precondition:
            object.__setattr__(self, "precondition", has_div_chunks)

    def run_item(self, item: Item) -> Item:
        from kmd.text_chunks.parse_divs import parse_divs_by_class

        if not item.body:
            raise InvalidInput(f"LLM actions expect a body: {self.name} on {item}")

        output = []
        chunks = parse_divs_by_class(item.body, self.chunk_class)

        with task_stack().context(self.name, len(chunks), "chunk") as ts:
            for chunk in chunks:
                output.append(self.process_chunk(chunk))
                ts.next()

        result_item = item.derived_copy(body="\n\n".join(output), format=Format.md_html)

        if self.title_template:
            result_item.title = self.title_template.format(
                title=(item.title or UNTITLED), action_name=self.name
            )

        return result_item

    def process_chunk(self, chunk: "TextNode") -> str:
        """
        Override to customize chunk handling.
        """
        from kmd.exec.llm_transforms import llm_transform_str
        from kmd.text_chunks.div_elements import div, div_get_original, div_insert_wrapped

        transform_input = div_get_original(chunk, child_name=ORIGINAL)
        llm_response = llm_transform_str(self, transform_input)
        new_div = div(RESULT, llm_response)

        return div_insert_wrapped(chunk, [new_div], container_class=CHUNK, original_class=ORIGINAL)
