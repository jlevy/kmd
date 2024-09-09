from kmd.exec.action_registry import kmd_action
from kmd.file_storage.workspaces import current_workspace
from kmd.media.media_download import download_and_transcribe
from kmd.model.actions_model import (
    CachedDocAction,
)
from kmd.model.file_formats_model import FileExt, Format
from kmd.model.items_model import Item, ItemType
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import is_audio_resource, is_url, is_video_resource
from kmd.text_chunks.parse_divs import parse_divs
from kmd.util.url import as_file_url

log = get_logger(__name__)


@kmd_action()
class Transcribe(CachedDocAction):
    def __init__(self):
        super().__init__(
            name="transcribe",
            description="Download and transcribe audio from a podcast or video.",
            precondition=is_url | is_audio_resource | is_video_resource,
        )

    def run_item(self, item: Item) -> Item:

        if item.url:
            url = item.url
        else:
            url = as_file_url(current_workspace().resolve_path(item))

        transcription = download_and_transcribe(url, language=self.language)

        result_item = item.derived_copy(
            type=ItemType.doc,
            body=transcription,
            format=Format.html,  # Important to note this since we put in timestamp span tags.
            file_ext=FileExt.html,
            external_path=None,
        )

        log.message("Got transcription: %s", parse_divs(transcription).size_summary(fast=True))

        return result_item
