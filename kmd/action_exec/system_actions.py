from kmd.action_defs import look_up_action

# This is used internally since we have special handling for URLs.
FETCH_ACTION_NAME = "fetch_page"
FETCH_ACTION = look_up_action(FETCH_ACTION_NAME, base_only=True)
