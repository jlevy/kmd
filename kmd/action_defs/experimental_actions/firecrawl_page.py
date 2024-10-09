from firecrawl import FirecrawlApp

from kmd.config.logger import get_logger
from kmd.config.settings import LogLevel
from kmd.errors import ApiResultError, InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.model import Item, PerItemAction
from kmd.model.file_formats_model import Format
from kmd.model.items_model import ItemType
from kmd.preconditions.precondition_defs import is_url

log = get_logger(__name__)


@kmd_action
class FirecrawlPage(PerItemAction):
    def __init__(self):
        super().__init__(
            name="firecrawl_page",
            description="Crawl a web page using Firecrawl's LLM-powered web crawler and save it in Markdown.",
            precondition=is_url,
            cachable=False,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput("Item must have a URL")

        firecrawl = FirecrawlApp()

        scrape_result = firecrawl.scrape_url(item.url, params={"formats": ["markdown"]})

        log.save_object("scrape_result", None, scrape_result, level=LogLevel.message)

        if "markdown" not in scrape_result:
            raise ApiResultError("No markdown found in scrape result")

        return item.derived_copy(
            type=ItemType.doc,
            format=Format.markdown,
            body=scrape_result["markdown"],
        )
