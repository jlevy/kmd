from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import Action, ActionInput, ActionResult, FileExt, Format, Item, ItemType, ONE_ARG
from kmd.preconditions.precondition_defs import is_config
from kmd.web_gen.video_gallery import video_gallery_generate

log = get_logger(__name__)


# FIXME: Combine with geneate_webpage as a single action, storing the config type in the config item.
@kmd_action
class VideoGalleryGenerate(Action):
    def __init__(self):
        super().__init__(
            name="video_gallery_generate",
            description="Generate a video gallery from a configured video gallery item.",
            expected_args=ONE_ARG,
            precondition=is_config,
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
