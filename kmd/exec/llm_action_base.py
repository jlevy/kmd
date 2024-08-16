from dataclasses import dataclass
from typing import Optional
from kmd.llms.llm_completion import llm_completion
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    ExpectedArgs,
    LLMMessage,
    LLMTemplate,
    CachedItemAction,
)
from kmd.model.errors_model import InvalidInput, UnexpectedError
from kmd.model.items_model import UNTITLED, Format, Item
from kmd.config import setup
from kmd.config.logger import get_logger
from kmd.model.language_models import LLM
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_defs import has_div_chunks, is_readable_text
from kmd.text_docs.div_chunks import parse_chunk_divs, chunk_wrapper
from kmd.text_docs.text_diffs import DiffFilterType, DiffFilter
from kmd.text_docs.text_doc import TextDoc
from kmd.text_docs.sliding_transforms import (
    WindowSettings,
    filtered_transform,
)
from kmd.text_formatting.html_in_md import html_div, join_blocks
from kmd.util.log_calls import log_calls

log = get_logger(__name__)


def _sliding_llm_transform(
    model: LLM,
    system_message: LLMMessage,
    template: LLMTemplate,
    input: str,
    windowing: Optional[WindowSettings],
    diff_filter: DiffFilter,
) -> str:
    def llm_transform(input_doc: TextDoc) -> TextDoc:
        return TextDoc.from_text(
            llm_completion(
                model,
                system_message=system_message,
                template=template,
                input=input_doc.reassemble(),
            )
        )

    input_doc = TextDoc.from_text(input)
    result_doc = filtered_transform(input_doc, llm_transform, windowing, diff_filter)

    return result_doc.reassemble()


@dataclass(frozen=True)
class LLMAction(CachedItemAction):
    expected_args: ExpectedArgs = ONE_OR_MORE_ARGS
    precondition: Precondition = is_readable_text

    windowing: Optional[WindowSettings] = None
    diff_filter: Optional[DiffFilterType] = None

    def run_item(self, item: Item) -> Item:
        return run_llm_transform(self, item)


@log_calls(level="message")
def run_llm_transform(action: LLMAction, item: Item) -> Item:
    """
    Run an LLM transform action on the input, optionally using a sliding window.
    """

    if not item.body:
        raise InvalidInput(f"LLM actions expect a body: {action.name} on {item}")
    if not action.model or not action.system_message or not action.template:
        raise InvalidInput(
            f"LLM actions expect a model, system_message, and template: {action.name}"
        )

    setup.api_setup()
    log.message(
        "Running LLM sliding transform action %s with model %s: %s %s",
        action.name,
        action.model,
        action.windowing,
        "with filter" if action.diff_filter else "without filter",  # TODO: Give filters names.
    )
    log.info("Input item: %s", item)

    result_item = item.derived_copy(body=None, format=Format.markdown)

    if action.windowing:
        diff_filter = action.diff_filter or DiffFilterType.accept_all
        result_item.body = _sliding_llm_transform(
            action.model,
            action.system_message,
            action.template,
            item.body,
            action.windowing,
            diff_filter.get_filter(),
        )
    else:
        result_item.body = llm_completion(
            action.model,
            system_message=action.system_message,
            template=action.template,
            input=item.body,
        )

    if action.title_template:
        result_item.title = action.title_template.format(
            title=(item.title or UNTITLED), action_name=action.name
        )

    return result_item


@dataclass(frozen=True)
class ChunkedLLMAction(LLMAction):
    """
    LLM action that operates on chunks that are already marked with divs.
    """

    precondition: Precondition = has_div_chunks

    result_class_name: str = "result"
    original_class_name: str = "original"

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput(f"LLM actions expect a body: {self.name} on {item}")
        if not self.model or not self.system_message or not self.template:
            raise UnexpectedError("LLM action missing parameters")

        output = []
        for chunk in parse_chunk_divs(item.body):
            llm_response = llm_completion(
                self.model,
                system_message=self.system_message,
                template=self.template,
                input=chunk.content,
            )

            output.append(
                chunk_wrapper(
                    join_blocks(
                        html_div(llm_response, self.result_class_name, padding="\n\n"),
                        html_div(
                            chunk.content, self.original_class_name, safe=True, padding="\n\n"
                        ),
                    )
                )
            )

        result_item = item.derived_copy(body="\n\n".join(output), format=Format.md_html)

        if self.title_template:
            result_item.title = self.title_template.format(
                title=(item.title or UNTITLED), action_name=self.name
            )

        return result_item
