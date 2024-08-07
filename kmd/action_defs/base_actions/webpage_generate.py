from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import ONE_ARG, Action, ActionInput, ActionResult
from kmd.model.items_model import FileExt, Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import is_config
from kmd.web_gen.tabbed_webpage import webpage_generate

log = get_logger(__name__)


@kmd_action
class GenerateWebpage(Action):
    def __init__(self):
        super().__init__(
            name="webpage_generate",
            description="Generate a web page from a configured web page item.",
            expected_args=ONE_ARG,
            precondition=is_config,
        )

    def run(self, items: ActionInput) -> ActionResult:
        config_item = items[0]
        html = webpage_generate(config_item)

        webpage_item = Item(
            title=config_item.title,
            type=ItemType.export,
            format=Format.html,
            file_ext=FileExt.html,
            body=html,
        )

        return ActionResult([webpage_item])
