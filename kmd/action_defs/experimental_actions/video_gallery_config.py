from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import Action, ActionInput, ActionResult
from kmd.preconditions.precondition_defs import has_text_body
from kmd.web_gen.video_gallery import video_gallery_config

log = get_logger(__name__)


@kmd_action
class VideoGalleryConfig(Action):
    def __init__(self):
        super().__init__(
            name="video_gallery_config",
            description="Set up a video gallery config with YouTube videos and their descriptions.",
            precondition=has_text_body,
        )

    def run(self, items: ActionInput) -> ActionResult:
        config_item = video_gallery_config(items)
        return ActionResult([config_item])
