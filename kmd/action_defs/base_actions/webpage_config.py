from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.model import Action, ActionInput, ActionResult
from kmd.web_gen.tabbed_webpage import webpage_config

log = get_logger(__name__)


@kmd_action
class WebpageConfig(Action):

    name: str = "webpage_config"

    description: str = """
        Set up a web page config with optional tabs for each page of content. Uses first item as the page title.
        """

    def run(self, items: ActionInput) -> ActionResult:
        for item in items:
            if not item.body:
                raise InvalidInput(f"Item must have a body: {item}")

        config_item = webpage_config(items)

        return ActionResult([config_item])
