from kmd.actions.action_registry import kmd_action
from kmd.media import web
from kmd.model.actions_model import ONE_OR_MORE_ARGS, Action, ActionInput, ActionResult
from kmd.model.errors_model import InvalidInput
from kmd.util.type_utils import not_none
from kmd.config.logger import get_logger

log = get_logger(__name__)


@kmd_action
class FetchPage(Action):
    def __init__(self):
        super().__init__(
            name="fetch_page",
            friendly_name="Fetch Page Details",
            description="Fetches the title, description, and body of a web page.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run(self, items: ActionInput) -> ActionResult:
        for item in items:
            if not item.url:
                raise InvalidInput(f"Item must have a URL: {item}")

        result_items = []
        for item in items:
            page_data = web.fetch_extract(not_none(item.url))
            fetched_item = item.new_copy_with(
                title=page_data.title, description=page_data.description, body=page_data.content
            )
            result_items.append(fetched_item)

        return ActionResult(result_items, replaces_input=True)
