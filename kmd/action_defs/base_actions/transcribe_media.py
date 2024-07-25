from kmd.action_exec.action_registry import kmd_action
from kmd.media.media_services import download_and_transcribe
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    EachItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import UNTITLED, FileExt, Format, Item, ItemType
from kmd.config.logger import get_logger

log = get_logger(__name__)


@kmd_action
class TranscribeMedia(EachItemAction):
    def __init__(self):
        super().__init__(
            name="transcribe_media",
            description="Download and transcribe audio from a podcast or video.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run_item(self, item: Item) -> Item:
        if not item.url:
            raise InvalidInput("Item must have a URL")

        transcription = download_and_transcribe(item.url)
        title = item.title or UNTITLED  # This shouldn't happen normally.
        result_title = f"{title} (transcription)"
        result_item = item.derived_copy(
            type=ItemType.note,
            title=result_title,
            body=transcription,
            format=Format.md_html,  # Important to note this since we put in timestamp spans.
            file_ext=FileExt.md,
        )

        return result_item
