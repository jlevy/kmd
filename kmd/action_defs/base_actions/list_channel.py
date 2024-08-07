from kmd.media.media_services import canonicalize_media_url, list_channel_items
from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import (
    Action,
    ActionInput,
    ActionResult,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import is_url

log = get_logger(__name__)


@kmd_action
class ListChannel(Action):
    def __init__(self):
        super().__init__(
            name="list_channel",
            description="Get the URL of every audio or video item in a given media channel (YouTube, Apple Podcasts, etc.).",
            precondition=is_url,
        )

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        if not item.url:
            raise InvalidInput("Item must have a URL")
        if not canonicalize_media_url(item.url):
            raise InvalidInput("Media format not supported")

        metadata_list = list_channel_items(item.url)

        result_items = []
        for metadata in metadata_list:
            if not canonicalize_media_url(metadata.url):
                log.warning("Skipping non-recognized video URL: %s", metadata.url)
                continue

            item = Item.from_media_metadata(metadata)
            result_items.append(item)

        return ActionResult(result_items)
