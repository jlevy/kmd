from kmd.exec.action_registry import kmd_action
from kmd.media.media_download import download_and_transcribe
from kmd.model.actions_model import (
    CachedDocAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import FileExt, Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import is_url

log = get_logger(__name__)


@kmd_action()
class Transcribe(CachedDocAction):
    def __init__(self):
        super().__init__(
            name="transcribe",
            description="Download and transcribe audio from a podcast or video.",
            precondition=is_url,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput("Item must have a URL")

        transcription = download_and_transcribe(item.url, language=self.language)
        result_item = item.derived_copy(
            type=ItemType.note,
            body=transcription,
            format=Format.html,  # Important to note this since we put in timestamp spans.
            file_ext=FileExt.md,
        )

        return result_item
