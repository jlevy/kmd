from dataclasses import asdict
import os
from exa_py import Exa

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.file_formats.yaml_util import to_yaml_string
from kmd.model import Item, PerItemAction
from kmd.model.file_formats_model import Format
from kmd.model.items_model import ItemType

log = get_logger(__name__)


@kmd_action
class WebSearchTopic(PerItemAction):
    def __init__(self):
        super().__init__(
            name="web_search_topic",
            description="Search the web for information on a topic.",
        )

    def run_item(self, item: Item) -> Item:
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

        return item.derived_copy(
            type=ItemType.doc,
            format=Format.yaml,
            body=to_yaml_string([asdict(r) for r in response.results]),
        )
