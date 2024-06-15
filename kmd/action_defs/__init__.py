from typing import Dict
from cachetools import cached
from kmd.action_defs.compound_actions import import_compound_actions
from kmd.config.logger import get_logger
from kmd.model.actions_model import Action
from kmd.action_exec.action_registry import instantiate_actions
from kmd.action_defs.base_actions import import_base_actions

log = get_logger(__name__)


@cached({})
def load_all_actions(base_only: bool = False) -> Dict[str, Action]:
    import_base_actions()
    # Allow bootstrapping base actions before compound actions.
    if not base_only:
        import_compound_actions()

    actions_map = instantiate_actions()

    log.info("Registered actions: %s", list(actions_map.keys()))
    return actions_map


def look_up_action(action_name: str, base_only: bool = False) -> Action:
    actions = load_all_actions(base_only=base_only)
    return actions[action_name]
