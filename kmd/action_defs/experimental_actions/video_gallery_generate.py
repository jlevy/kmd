from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import ONE_ARG, Action, ActionInput, ActionResult
from kmd.model.items_model import FileExt, Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.web_gen.video_gallery import video_gallery_generate

log = get_logger(__name__)


# FIXME: Combine with geneate_webpage as a single action, storing the config type in the config item.
@kmd_action
class GenerateVideoGallery(Action):
    def __init__(self):
        super().__init__(
            name="video_gallery_generate",
            description="Generate a video gallery from a configured video gallery item.",
            expected_args=ONE_ARG,
        )

    def run(self, items: ActionInput) -> ActionResult:
        config_item = items[0]
        html = video_gallery_generate(config_item)

        gallery_item = Item(
            title=config_item.title,
            type=ItemType.export,
            format=Format.html,
            file_ext=FileExt.html,
            body=html,
        )

        return ActionResult([gallery_item])
