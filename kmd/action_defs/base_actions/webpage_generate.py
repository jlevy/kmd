from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import (
    Action,
    ActionInput,
    ActionResult,
    ArgCount,
    FileExt,
    Format,
    Item,
    ItemType,
    ONE_ARG,
    Precondition,
)
from kmd.preconditions.precondition_defs import is_config
from kmd.web_gen.tabbed_webpage import webpage_generate

log = get_logger(__name__)


@kmd_action
class WebpageGenerate(Action):

    name: str = "webpage_generate"

    description: str = "Generate a web page from a configured web page item."

    expected_args: ArgCount = ONE_ARG

    precondition: Precondition = is_config

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
