from dataclasses import dataclass
import logging
from kmd.actions.models import LLM
from kmd.apis.openai import openai_completion
from kmd.model.items import Item, copy_with
from kmd import config


log = logging.getLogger(__name__)


@dataclass
class Action:
    name: str
    description: str
    model: LLM
    system_message: str
    template: str


def run_action(action: Action, item: Item) -> Item:
    assert item.body is not None

    config.api_setup()

    log.info("Running action %s on item %s", action.name, item)

    output_item = copy_with(item, body=None)

    # FIXME: Handle more action types and models.
    llm_input = action.template.format(body=item.body)
    llm_output = openai_completion(
        action.model.value, system_message=action.system_message, user_message=llm_input
    )

    output_item.body = llm_output
    return output_item
