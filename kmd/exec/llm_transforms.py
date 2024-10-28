from typing import cast, Optional

from kmd.config import setup
from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.llms.llm_completion import llm_template_completion
from kmd.model.actions_model import ExecContext
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType, UNTITLED
from kmd.model.language_models import LLM
from kmd.model.llm_actions_model import LLMAction
from kmd.model.messages_model import Message, MessageTemplate
from kmd.text_docs.diff_filters import accept_all, DiffFilter
from kmd.text_docs.sliding_transforms import filtered_transform, WindowSettings
from kmd.text_docs.text_doc import TextDoc
from kmd.text_formatting.markdown_normalization import normalize_markdown

log = get_logger(__name__)


def windowed_llm_transform(
    model: LLM,
    system_message: Message,
    template: MessageTemplate,
    input: str,
    windowing: Optional[WindowSettings],
    diff_filter: DiffFilter,
    check_no_results: bool = True,
    context: Optional[ExecContext] = None,
) -> TextDoc:
    def doc_transform(input_doc: TextDoc) -> TextDoc:
        return TextDoc.from_text(
            # XXX We normalize the Markdown before parsing as a text doc in particular because we
            # want bulleted list items to be separate paragraphs.
            normalize_markdown(
                llm_template_completion(
                    model,
                    system_message=system_message,
                    input=input_doc.reassemble(),
                    template=template,
                    check_no_results=check_no_results,
                ).content
            )
        )

    result_doc = filtered_transform(
        TextDoc.from_text(input), doc_transform, windowing, diff_filter, context
    )

    return result_doc


def llm_transform_str(context: ExecContext, input_str: str, check_no_results: bool = True) -> str:
    assert isinstance(context.action, LLMAction)
    action = cast(LLMAction, context.action)

    if not action.model:
        raise InvalidInput(f"LLM action `{action.name}` is missing a model")
    if not action.system_message:
        raise InvalidInput(f"LLM action `{action.name}` is missing a system message")
    if not action.template:
        raise InvalidInput(f"LLM action `{action.name}` is missing a template")

    setup.api_setup()

    if action.windowing and action.windowing.size:
        log.message(
            "Running LLM `%s` sliding transform for action `%s`: %s %s",
            action.model,
            action.name,
            action.windowing,
            "with filter" if action.diff_filter else "without filter",  # TODO: Give filters names.
        )
        diff_filter = action.diff_filter or accept_all

        result_str = windowed_llm_transform(
            action.model,
            action.system_message,
            action.template,
            input_str,
            action.windowing,
            diff_filter,
            context=context,
        ).reassemble()
    else:
        log.message(
            "Running simple LLM transform action `%s` with model %s",
            action.name,
            action.model,
        )

        result_str = llm_template_completion(
            action.model,
            system_message=action.system_message,
            template=action.template,
            input=input_str,
            check_no_results=check_no_results,
        ).content

    return result_str


def llm_transform_item(context: ExecContext, item: Item) -> Item:
    """
    Run an LLM transform action on the input, optionally using a sliding window.
    """
    action = context.action
    if not item.body:
        raise InvalidInput(f"LLM actions expect a body: {action.name} on {item}")

    log.info("LLM transform on item: %s", item)

    result_item = item.derived_copy(type=ItemType.doc, body=None, format=Format.markdown)

    result_item.body = llm_transform_str(context, item.body)

    if action.title_template:
        result_item.title = action.title_template.format(
            title=(item.title or UNTITLED), action_name=action.name
        )

    return result_item
