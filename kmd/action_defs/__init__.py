from typing import Dict
from cachetools import Cache, cached
from kmd.action_defs.compound_actions import import_compound_actions
from kmd.action_defs.experimental_actions import import_experimental_actions
from kmd.config.logger import get_logger
from kmd.model.actions_model import Action
from kmd.action_exec.action_registry import instantiate_actions
from kmd.action_defs.base_actions import import_base_actions
from kmd.model.errors_model import InvalidInput

log = get_logger(__name__)


cache = Cache(maxsize=float("inf"))


@cached(cache)
def load_all_actions(base_only: bool = False) -> Dict[str, Action]:
    import_base_actions()
    # Allow bootstrapping base actions before compound actions.
    if not base_only:
        import_experimental_actions()
        import_compound_actions()

    actions_map = instantiate_actions()

    log.info(
        "Loaded %s actions (base_only=%s)",
        len(actions_map),
        base_only,
    )

    return actions_map


def reload_all_actions(base_only: bool = False) -> Dict[str, Action]:
    cache.clear()
    return load_all_actions(base_only=base_only)


def look_up_action(action_name: str, base_only: bool = False) -> Action:
    actions = load_all_actions(base_only=base_only)
    if action_name not in actions:
        raise InvalidInput(f"Action not found: {action_name}")
    return actions[action_name]
