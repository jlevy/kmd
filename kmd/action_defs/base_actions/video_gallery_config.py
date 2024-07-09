from kmd.action_exec.action_registry import kmd_action
from kmd.model.actions_model import ONE_OR_MORE_ARGS, Action, ActionInput, ActionResult
from kmd.config.logger import get_logger
from kmd.web_gen.video_gallery import video_gallery_config

log = get_logger(__name__)


@kmd_action
class ConfigureVideoGallery(Action):
    def __init__(self):
        super().__init__(
            name="configure_video_gallery",
            description="Set up a video gallery config with YouTube videos and their descriptions.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run(self, items: ActionInput) -> ActionResult:
        config_item = video_gallery_config(items)
        return ActionResult([config_item])
