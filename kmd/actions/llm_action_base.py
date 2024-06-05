from dataclasses import dataclass
from textwrap import indent
from typing import List, Optional
from slugify import slugify
from kmd.llms.completion import completion
from kmd.model.actions_model import Action, ActionInput, ActionResult, ONE_OR_MORE_ARGS
from kmd.model.items_model import Format, Item
from kmd.config import setup
from kmd.config.logger import get_logger
from kmd.text_handling.text_diffs import ALL_CHANGES, DiffOpFilter
from kmd.text_handling.text_doc import TextDoc
from kmd.text_handling.sliding_transforms import (
    WindowSettings,
    filtered_transform,
)
from kmd.util.log_calls import log_calls

log = get_logger(__name__)


@dataclass
class LLMAction(Action):
    def __init__(
        self,
        name,
        friendly_name,
        description,
        model,
        system_message,
        title_template,
        template,
        windowing: Optional[WindowSettings] = None,
        diff_filter: Optional[DiffOpFilter] = None,
    ):
        super().__init__(
            name,
            friendly_name,
            description,
            model=model,
            system_message=system_message,
            title_template=title_template,
            template=template,
            expected_args=ONE_OR_MORE_ARGS,
        )
        self.implementation: str = "llm"
        self.windowing = windowing
        self.diff_filter = diff_filter

    def run(self, items: ActionInput) -> ActionResult:
        return run_llm_action(self, items)


@log_calls(level="message")
def llm_completion(model: str, system_message: str, template: str, input: str) -> str:
    user_message = template.format(body=input)
    model_slug = slugify(model, separator="_")

    log.info("LLM completion input to model %s:\n%s", model, indent(user_message, "    "))
    log.save_object("LLM system message", f"llm.{model_slug}.system_message", system_message)
    log.save_object("LLM user message", f"llm.{model_slug}.user_message", user_message)

    text_output = completion(
        model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )

    log.info("LLM completion output:\n%s", indent(text_output, "    "))
    log.save_object("LLM output", f"llm.{model_slug}.output", text_output)

    return text_output


def _sliding_llm_transform(
    model: str,
    system_message: str,
    template: str,
    input: str,
    windowing: Optional[WindowSettings],
    diff_filter: DiffOpFilter,
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


@log_calls(level="message")
def run_llm_action(action: LLMAction, items: ActionInput) -> ActionResult:
    result_items: List[Item] = []
    for item in items:
        if not item.body:
            raise ValueError(f"LLM actions expect a body: {action.name} on {item}")
        if not action.model or not action.system_message or not action.template:
            raise ValueError(
                f"LLM actions expect a model, system_message, and template: {action.name}"
            )

        setup.api_setup()

        log.message(
            "Running LLM action %s with model %s: %s %s",
            action.name,
            action.model,
            action.windowing,
            "with filter" if action.diff_filter else "without filter",  # TODO: Give filters names.
        )
        log.info("Input item: %s", item)

        result_item = item.derived_copy(body=None)
        result_item.body = _sliding_llm_transform(
            action.model,
            action.system_message,
            action.template,
            item.body,
            action.windowing,
            action.diff_filter or ALL_CHANGES,
        )

        if action.title_template:
            result_item.title = action.title_template.format(title=item.abbrev_title())
        result_item.format = Format.markdown

        result_items.append(result_item)

    return ActionResult(result_items)
