from dataclasses import dataclass
from typing import List
from kmd.media import web
from kmd.model.model import Action, Item


# For now these are simple but we may want to support other hints or output data in the future.
ActionInput = List[Item]
ActionResult = List[Item]


@dataclass
class CrawlAction(Action):
    name = "Fetch Page Title and Details"
    description = "Fetches the title, description, and body of a web page."

    def __init__(self):
        super().__init__(name=self.name, description=self.description)

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        if not item.url:
            raise ValueError("Item must have a URL")
        page_data = web.fetch_extract(item.url)
        item.title = page_data.title
        item.description = page_data.description
        item.body = page_data.content
        return [item]
