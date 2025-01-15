from typing import TYPE_CHECKING

from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.llms.fuzzy_parsing import strip_markdown_fence
from kmd.model.actions_model import ActionInput, ActionResult, PerItemAction
from kmd.model.doc_elements import CHUNK, ORIGINAL, RESULT
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, UNTITLED
from kmd.model.language_models import DEFAULT_CAREFUL_LLM, LLM
from kmd.model.params_model import common_params, ParamList
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_defs import is_text_doc
from kmd.util.task_stack import task_stack

if TYPE_CHECKING:
    from kmd.text_chunks.text_node import TextNode

log = get_logger(__name__)


@dataclass
class LLMAction(PerItemAction):
    """
    Base LLM action that processes each item one at a time.
    """

    model: LLM = DEFAULT_CAREFUL_LLM

    precondition: Precondition = is_text_doc

    params: ParamList = common_params("model")

    def run(self, items: ActionInput) -> ActionResult:
        log.info("Running LLM action `%s`.", self.name)
        return super().run(items)

    def run_item(self, item: Item) -> Item:
        """
        Override to customize item handling.
        """
        from kmd.exec.llm_transforms import llm_transform_item
        from kmd.text_wrap.markdown_normalization import normalize_markdown

        item = llm_transform_item(self.context(), item)
        if item.body:
            # Both these should be safe for almost all LLM outputs.
            item.body = strip_markdown_fence(item.body)
            item.body = normalize_markdown(item.body)
        return item


@dataclass
class ChunkedLLMAction(LLMAction):
    """
    Base class for LLM actions that operate on chunks that are already marked with divs.
    """

    precondition: Precondition = Precondition.always

    chunk_class: str = CHUNK

    def __post_init__(self):
        from kmd.preconditions.precondition_defs import has_div_chunks

        if not self.precondition:
            self.precondition = has_div_chunks

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

        result_item = item.derived_copy(
            type=item.type, body="\n\n".join(output), format=Format.md_html
        )

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
        llm_response = llm_transform_str(self.context(), transform_input)
        new_div = div(RESULT, llm_response)

        return div_insert_wrapped(chunk, [new_div], container_class=CHUNK, original_class=ORIGINAL)
