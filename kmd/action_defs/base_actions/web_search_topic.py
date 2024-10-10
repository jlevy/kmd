import os
from typing import List

from exa_py import Exa

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.model import Item
from kmd.model.actions_model import Action, ActionInput, ActionResult, ONE_ARG
from kmd.model.file_formats_model import Format
from kmd.model.items_model import ItemType

log = get_logger(__name__)


@kmd_action
class WebSearchTopic(Action):
    def __init__(self):
        super().__init__(
            name="web_search_topic",
            description="Search the web for information on a topic.",
            expected_args=ONE_ARG,
        )

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        if not item.body:
            raise InvalidInput("Item must have a body")

        exa = Exa(api_key=os.getenv("EXA_API_KEY"))

        response = exa.search_and_contents(
            item.body,
            type="neural",
            use_autoprompt=True,
            num_results=10,
            text=True,
        )
        log.message("Got Exa response: %s results", len(response.results))

        # yaml_item = item.derived_copy(
        #     type=ItemType.doc,
        #     format=Format.yaml,
        #     body=to_yaml_string([asdict(r) for r in response.results]),
        # )

        results_items: List[Item] = []
        for result in response.results:
            log.message("Result: %s", result.title)

            results_items.append(
                item.derived_copy(
                    type=ItemType.doc,
                    format=Format.markdown,
                    title=result.title,
                    created=result.published_date,
                    thumbnail_url=result.image,
                    body=result.text,
                )
            )

        return ActionResult(items=results_items)
