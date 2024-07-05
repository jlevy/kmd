from kmd.action_defs import look_up_action
from kmd.model.actions_model import Action
from kmd.util.lazyobject import lazyobject


# This is used internally since we have special handling for URLs.
FETCH_PAGE_METADATA_NAME = "fetch_page_metadata"


@lazyobject
def fetch_page_metadata() -> Action:
    return look_up_action(FETCH_PAGE_METADATA_NAME, base_only=True)
