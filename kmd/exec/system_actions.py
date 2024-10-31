from kmd.action_defs import look_up_action
from kmd.model.actions_model import Action
from kmd.util.lazyobject import lazyobject


@lazyobject
def fetch_page_metadata() -> Action:
    return look_up_action("fetch_page_metadata", base_only=True)
