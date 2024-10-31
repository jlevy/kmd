from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.media.media_tools import cache_and_transcribe
from kmd.model import common_params, FileExt, Format, Item, ItemType, ParamList, PerItemAction
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_defs import is_audio_resource, is_url_item, is_video_resource
from kmd.text_chunks.parse_divs import parse_divs
from kmd.util.type_utils import not_none
from kmd.util.url import as_file_url
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


@kmd_action
@dataclass
class Transcribe(PerItemAction):

    name: str = "transcribe"

    description: str = "Download and transcribe audio from a podcast or video."

    precondition: Precondition = is_url_item | is_audio_resource | is_video_resource

    params: ParamList = common_params("language")

    language: str = "en"

    def run_item(self, item: Item) -> Item:

        if item.url:
            url = item.url
        else:
            url = as_file_url(current_workspace().base_dir / not_none(item.store_path))

        transcription = cache_and_transcribe(url, language=self.language)

        result_item = item.derived_copy(
            type=ItemType.doc,
            body=transcription,
            format=Format.html,  # Important to note this since we put in timestamp span tags.
            file_ext=FileExt.html,
            external_path=None,
        )

        log.message("Got transcription: %s", parse_divs(transcription).size_summary(fast=True))

        return result_item
