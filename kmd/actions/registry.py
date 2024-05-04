import logging
from typing import Callable, Dict, List

from cachetools import cached

from kmd.actions.actions import Action
from kmd.model.items import Item

log = logging.getLogger(__name__)

_action_functions = []


def register_action(function: Callable[[List[Item]], Item]):
    """
    Annotation to make it easy to register a function that implements an action.
    """

    _action_functions.append(function)
    return function


@cached({})
def load_all_actions() -> Dict[str, Callable[[List[Item]], Item]]:
    # Import to register the actions.
    import kmd.actions.action_definitions

    action_functions_map = {}
    for f in _action_functions:
        action_functions_map[f.__name__] = f

    if not action_functions_map:
        raise ValueError("No actions registered.")

    log.info("Registered actions: %s", action_functions_map.keys())
    return action_functions_map
