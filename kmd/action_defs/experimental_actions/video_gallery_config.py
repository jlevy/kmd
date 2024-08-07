from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import ONE_OR_MORE_ARGS, Action, ActionInput, ActionResult
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import has_text_body
from kmd.web_gen.video_gallery import video_gallery_config

log = get_logger(__name__)


@kmd_action
class ConfigureVideoGallery(Action):
    def __init__(self):
        super().__init__(
            name="video_gallery_conifg",
            description="Set up a video gallery config with YouTube videos and their descriptions.",
            expected_args=ONE_OR_MORE_ARGS,
            precondition=has_text_body,
        )

    def run(self, items: ActionInput) -> ActionResult:
        config_item = video_gallery_config(items)
        return ActionResult([config_item])
