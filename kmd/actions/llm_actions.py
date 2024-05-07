from dataclasses import dataclass
from enum import Enum
import logging
from kmd.actions.action_lib import ActionResult
from kmd.apis.openai import openai_completion
from kmd.model.model import Action, Format, Item
from kmd import config

log = logging.getLogger(__name__)

# TODO: Handle more services and models.


class LLM(Enum):
    gpt_3_5_turbo_16k_0613 = "gpt-3.5-turbo-16k-0613"


@dataclass
class LLMAction(Action):
    implementation: str = "llm"

    def run(self, item: Item) -> ActionResult:
        return run_llm_action(self, item)


def run_llm_action(action: LLMAction, item: Item) -> ActionResult:
    if not item.body:
        raise ValueError("LLM actions expect a body")
    if not action.model or not action.system_message or not action.template:
        raise ValueError("LLM actions expect a model, system_message, and template")

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

    return [output_item]
