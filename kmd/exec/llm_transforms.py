from typing import Optional
from kmd.llms.llm_completion import llm_completion
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import UNTITLED, Format, Item
from kmd.config import setup
from kmd.config.logger import get_logger
from kmd.model.language_models import LLM
from kmd.model.llm_actions_model import LLMAction
from kmd.model.llm_message_model import LLMMessage, LLMTemplate
from kmd.text_docs.text_diffs import DiffFilterType, DiffFilter
from kmd.text_docs.text_doc import TextDoc
from kmd.text_docs.sliding_transforms import (
    WindowSettings,
    filtered_transform,
)

log = get_logger(__name__)


def windowed_llm_transform(
    model: LLM,
    system_message: LLMMessage,
    template: LLMTemplate,
    input: str,
    windowing: Optional[WindowSettings],
    diff_filter: DiffFilter,
) -> TextDoc:
    def doc_transform(input_doc: TextDoc) -> TextDoc:
        return TextDoc.from_text(
            llm_completion(
                model,
                system_message=system_message,
                template=template,
                input=input_doc.reassemble(),
            )
        )

    result_doc = filtered_transform(TextDoc.from_text(input), doc_transform, windowing, diff_filter)

    return result_doc


def llm_transform_str(action: LLMAction, input_str: str) -> str:
    if not action.model or not action.system_message or not action.template:
        raise InvalidInput(
            f"LLM actions expect a model, system_message, and template: {action.name}"
        )

    if action.windowing:
        diff_filter = action.diff_filter or DiffFilterType.accept_all

        result_str = windowed_llm_transform(
            action.model,
            action.system_message,
            action.template,
            input_str,
            action.windowing,
            diff_filter.get_filter(),
        ).reassemble()
    else:
        result_str = llm_completion(
            action.model,
            system_message=action.system_message,
            template=action.template,
            input=input_str,
        )

    return result_str


def llm_transform_item(action: LLMAction, item: Item) -> Item:
    """
    Run an LLM transform action on the input, optionally using a sliding window.
    """

    if not item.body:
        raise InvalidInput(f"LLM actions expect a body: {action.name} on {item}")

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

    result_item.body = llm_transform_str(action, item.body)

    if action.title_template:
        result_item.title = action.title_template.format(
            title=(item.title or UNTITLED), action_name=action.name
        )

    return result_item
