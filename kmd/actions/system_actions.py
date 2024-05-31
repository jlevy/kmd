from kmd.actions.action_registry import look_up_action

FETCH_ACTION_NAME = "fetch_page"

# This is used internally since we have special handling for URLs.
FETCH_ACTION = look_up_action(FETCH_ACTION_NAME)
