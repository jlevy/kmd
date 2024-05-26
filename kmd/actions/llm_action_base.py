from dataclasses import dataclass
from enum import Enum
from kmd.apis.openai import openai_completion
from kmd.model.actions_model import Action, ActionInput, ActionResult, ONE_OR_MORE_ARGS
from kmd.model.items_model import Format
from kmd.file_storage.workspaces import current_workspace
from kmd.config import setup
from kmd.config.logger import get_logger

log = get_logger(__name__)


class LLM(Enum):
    gpt_3_5_turbo_16k_0613 = "gpt-3.5-turbo-16k-0613"
    gpt_4 = "gpt-4"
    gpt_4_turbo = "gpt-4-turbo"
    gpt_4o = "gpt-4o"


@dataclass
class LLMAction(Action):
    def __init__(
        self, name, friendly_name, description, model, system_message, title_template, template
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

    def run(self, items: ActionInput) -> ActionResult:
        return _run_llm_action(self, items)


def _run_llm_action(action: LLMAction, items: ActionInput) -> ActionResult:
    result_items = []
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

        llm_input = action.template.format(body=item.body)
        llm_output = openai_completion(
            action.model, system_message=action.system_message, user_message=llm_input
        )

        result_item.body = llm_output
        if action.title_template:
            result_item.title = action.title_template.format(title=item.get_title())
        result_item.format = Format.markdown

        current_workspace().save(result_item)

        result_items.append(result_item)

    return ActionResult(result_items)
