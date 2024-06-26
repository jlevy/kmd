from kmd.action_exec.action_registry import kmd_action
from kmd.model.actions_model import ONE_OR_MORE_ARGS, ONE_ARG, Action, ActionInput, ActionResult
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import FileExt, Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.web_gen.tabbed_webpage import configure_webpage, generate_webpage
from kmd.web_gen.video_gallery import configure_video_gallery, generate_video_gallery

log = get_logger(__name__)


@kmd_action
class ConfigureWebpage(Action):
    def __init__(self):
        super().__init__(
            name="configure_webpage",
            description="Set up a web page config with optional tabs for each page of content. Uses first item as the page title.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run(self, items: ActionInput) -> ActionResult:
        for item in items:
            if not item.body:
                raise InvalidInput(f"Item must have a body: {item}")

        config_item = configure_webpage(items)
        return ActionResult([config_item])


@kmd_action
class GenerateWebpage(Action):
    def __init__(self):
        super().__init__(
            name="generate_webpage",
            friendly_name="Generate Web Page",
            description="Generate a web page from a configured web page item.",
            expected_args=ONE_ARG,
        )

    def run(self, items: ActionInput) -> ActionResult:
        config_item = items[0]
        html = generate_webpage(config_item)

        webpage_item = Item(
            title=config_item.title,
            type=ItemType.export,
            format=Format.html,
            file_ext=FileExt.html,
            body=html,
        )

        return ActionResult([webpage_item])


@kmd_action
class ConfigureVideoGallery(Action):
    def __init__(self):
        super().__init__(
            name="configure_video_gallery",
            description="Set up a video gallery config with YouTube videos and their descriptions.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run(self, items: ActionInput) -> ActionResult:
        config_item = configure_video_gallery(items)
        return ActionResult([config_item])


# FIXME: Combine with geneate_webpage as a single action, storing the config type in the config item.
@kmd_action
class GenerateVideoGallery(Action):
    def __init__(self):
        super().__init__(
            name="generate_video_gallery",
            description="Generate a video gallery from a configured video gallery item.",
            expected_args=ONE_ARG,
        )

    def run(self, items: ActionInput) -> ActionResult:
        config_item = items[0]
        html = generate_video_gallery(config_item)

        gallery_item = Item(
            title=config_item.title,
            type=ItemType.export,
            format=Format.html,
            file_ext=FileExt.html,
            body=html,
        )

        return ActionResult([gallery_item])
