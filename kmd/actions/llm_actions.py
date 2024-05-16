from dataclasses import dataclass
from enum import Enum
import logging
from kmd.apis.openai import openai_completion
from kmd.model.actions_model import Action, ActionInput, ActionResult
from kmd.model.items_model import Format
from kmd.file_storage.workspaces import current_workspace
from kmd import config


log = logging.getLogger(__name__)

# TODO: Handle more services and models.


class LLM(Enum):
    gpt_3_5_turbo_16k_0613 = "gpt-3.5-turbo-16k-0613"


@dataclass
class LLMAction(Action):
    implementation: str = "llm"

    def run(self, items: ActionInput) -> ActionResult:
        return _run_llm_action(self, items)


def _run_llm_action(action: LLMAction, items: ActionInput) -> ActionResult:
    # For now LLM actions only support one input.
    if not items or len(items) != 1:
        raise ValueError(f"LLM actions expect a single item as input: {action.name} on {items}")
    item = items[0]

    if not item.body:
        raise ValueError(f"LLM actions expect a body: {action.name} on {item}")
    if not action.model or not action.system_message or not action.template:
        raise ValueError(f"LLM actions expect a model, system_message, and template: {action.name}")

    config.api_setup()

    log.info("Running action %s on item %s", action.name, item)

    output_item = item.copy_with(body=None)

    llm_input = action.template.format(body=item.body)
    llm_output = openai_completion(
        action.model, system_message=action.system_message, user_message=llm_input
    )

    output_item.body = llm_output
    if action.title_template:
        output_item.title = action.title_template.format(title=item.get_title())
    output_item.format = Format.markdown

    current_workspace().save(output_item)

    return ActionResult([output_item])
