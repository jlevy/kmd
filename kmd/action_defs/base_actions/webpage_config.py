from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import ONE_OR_MORE_ARGS, Action, ActionInput, ActionResult
from kmd.model.errors_model import InvalidInput
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import has_text_body
from kmd.web_gen.tabbed_webpage import webpage_config

log = get_logger(__name__)


@kmd_action
class WebpageConfig(Action):
    def __init__(self):
        super().__init__(
            name="webpage_config",
            description="Set up a web page config with optional tabs for each page of content. Uses first item as the page title.",
            expected_args=ONE_OR_MORE_ARGS,
            precondition=has_text_body,
        )

    def run(self, items: ActionInput) -> ActionResult:
        for item in items:
            if not item.body:
                raise InvalidInput(f"Item must have a body: {item}")

        config_item = webpage_config(items)

        return ActionResult([config_item])
