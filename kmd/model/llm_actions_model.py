from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional
from kmd.config.logger import get_logger
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    Action,
    ActionInput,
    ActionResult,
    CachedItemAction,
    ExpectedArgs,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.html_conventions import CHUNK
from kmd.model.items_model import UNTITLED, Format, Item
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_defs import has_div_chunks, is_readable_text
from kmd.text_chunks.parse_divs import parse_divs_by_class, TextNode
from kmd.text_docs.sliding_transforms import WindowSettings
from kmd.text_docs.text_diffs import DiffFilterType


log = get_logger(__name__)


@dataclass(frozen=True)
class LLMAction(Action):
    """
    Abstract base for LLM actions. Override with templates or other customizations.
    """

    expected_args: ExpectedArgs = ONE_OR_MORE_ARGS
    precondition: Optional[Precondition] = is_readable_text

    windowing: Optional[WindowSettings] = None
    diff_filter: Optional[DiffFilterType] = None

    @abstractmethod
    def run(self, items: ActionInput) -> ActionResult:
        pass


@dataclass(frozen=True)
class CachedItemLLMAction(LLMAction, CachedItemAction):
    """
    Abstract base LLM action that is also cached.
    """

    def run(self, items: ActionInput) -> ActionResult:
        return super(CachedItemAction, self).run(items)

    @abstractmethod
    def run_item(self, item: Item) -> Item:
        """
        A basic implementationn would be:

        return llm_transform_item(self, item)
        """
        pass


@dataclass(frozen=True)
class ChunkedLLMAction(CachedItemLLMAction):
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

    @abstractmethod
    def process_chunk(self, chunk: TextNode) -> str:
        """
        A basic implementationn would be:

        llm_response = llm_transform_str(self, chunk.contents)
        return insert_chunk_child(chunk, llm_response)
        """
        pass
