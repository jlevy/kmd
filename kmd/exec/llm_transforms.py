from typing import Optional

from kmd.config import setup
from kmd.config.logger import get_logger
from kmd.llms.llm_completion import llm_completion
from kmd.model.actions_model import TransformAction
from kmd.model.errors_model import InvalidInput
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, UNTITLED
from kmd.model.language_models import LLM
from kmd.model.messages_model import Message, MessageTemplate
from kmd.text_docs.sliding_transforms import filtered_transform, WindowSettings
from kmd.text_docs.text_diffs import DiffFilter, DiffFilterType
from kmd.text_docs.text_doc import TextDoc

log = get_logger(__name__)


def windowed_llm_transform(
    model: LLM,
    system_message: Message,
    template: MessageTemplate,
    input: str,
    windowing: Optional[WindowSettings],
    diff_filter: DiffFilter,
    check_no_results: bool = True,
) -> TextDoc:
    def doc_transform(input_doc: TextDoc) -> TextDoc:
        return TextDoc.from_text(
            llm_completion(
                model,
                system_message=system_message,
                template=template,
                input=input_doc.reassemble(),
                check_no_results=check_no_results,
            )
        )

    result_doc = filtered_transform(TextDoc.from_text(input), doc_transform, windowing, diff_filter)

    return result_doc


def llm_transform_str(
    action: TransformAction, input_str: str, check_no_results: bool = True
) -> str:
    if not action.model:
        raise InvalidInput(f"LLM action `{action.name}` is missing a model")
    if not action.system_message:
        raise InvalidInput(f"LLM action `{action.name}` is missing a system message")
    if not action.template:
        raise InvalidInput(f"LLM action `{action.name}` is missing a template")

    setup.api_setup()

    if action.windowing:
        log.message(
            "Running LLM sliding transform action `%s` with model %s: %s %s",
            action.name,
            action.model,
            action.windowing,
            "with filter" if action.diff_filter else "without filter",  # TODO: Give filters names.
        )
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
        log.message(
            "Running simple LLM transform action `%s` with model %s",
            action.name,
            action.model,
        )

        result_str = llm_completion(
            action.model,
            system_message=action.system_message,
            template=action.template,
            input=input_str,
            check_no_results=check_no_results,
        )

    return result_str


def llm_transform_item(action: TransformAction, item: Item) -> Item:
    """
    Run an LLM transform action on the input, optionally using a sliding window.
    """

    if not item.body:
        raise InvalidInput(f"LLM actions expect a body: {action.name} on {item}")

    log.info("LLM transform in item: %s", item)

    result_item = item.derived_copy(body=None, format=Format.markdown)

    result_item.body = llm_transform_str(action, item.body)

    if action.title_template:
        result_item.title = action.title_template.format(
            title=(item.title or UNTITLED), action_name=action.name
        )

    return result_item
