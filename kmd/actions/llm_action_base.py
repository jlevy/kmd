from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from kmd.llms.completion import completion
from kmd.model.actions_model import Action, ActionInput, ActionResult, ONE_OR_MORE_ARGS
from kmd.model.items_model import Format, Item
from kmd.file_storage.workspaces import current_workspace
from kmd.config import setup
from kmd.config.logger import get_logger
from kmd.text_handling.text_diffs import DiffOpFilter
from kmd.text_handling.text_doc import TextDoc
from kmd.text_handling.windowing import WindowSettings, sliding_transform
from kmd.util.log_calls import log_calls

log = get_logger(__name__)


class LLM(Enum):
    gpt_3_5_turbo_16k_0613 = "gpt-3.5-turbo-16k-0613"
    gpt_4 = "gpt-4"
    gpt_4_turbo = "gpt-4-turbo"
    gpt_4o = "gpt-4o"


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
        window_settings: Optional[WindowSettings] = None,
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
        self.window_settings = window_settings
        self.diff_filter = diff_filter

    def run(self, items: ActionInput) -> ActionResult:
        return run_llm_action(self, items)


@log_calls(level="message")
def llm_completion(model: str, system_message: str, template: str, input: str) -> str:
    user_message = template.format(body=input)
    text_output = completion(
        model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )
    return text_output


def _sliding_llm_transform(
    model: str,
    system_message: str,
    template: str,
    input: str,
    window_settings: Optional[WindowSettings],
) -> str:
    if not window_settings:
        result_str = llm_completion(model, system_message, template, input)
    else:

        def transform(text_doc: TextDoc):
            return TextDoc.from_text(
                llm_completion(model, system_message, template, text_doc.reassemble())
            )

        input_doc = TextDoc.from_text(input)
        transformed_doc = sliding_transform(
            input_doc,
            transform,
            window_settings,
        )
        result_str = transformed_doc.reassemble()

    # FIXME: Add diff filtering here.
    return result_str


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

        log.info("Running action %s on item %s", action.name, item)

        result_item = item.new_copy_with(body=None)
        result_item.body = _sliding_llm_transform(
            action.model,
            action.system_message,
            action.template,
            item.body,
            action.window_settings,
        )

        if action.title_template:
            result_item.title = action.title_template.format(title=item.get_title())
        result_item.format = Format.markdown

        current_workspace().save(result_item)

        result_items.append(result_item)

    return ActionResult(result_items)
