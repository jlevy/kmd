from kmd.action_defs import look_up_action
from kmd.model.actions_model import Action
from kmd.util.lazyobject import lazyobject

# This is used internally since we have special handling for URLs.
FETCH_ACTION_NAME = "fetch_page"


@lazyobject
def fetch_action() -> Action:
    return look_up_action(FETCH_ACTION_NAME, base_only=True)
