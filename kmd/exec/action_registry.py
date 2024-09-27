from typing import Callable, Dict, List, Type

from kmd.config.logger import get_logger
from kmd.config.text_styles import EMOJI_WARN
from kmd.model.actions_model import Action

log = get_logger(__name__)

ActionWrapper = Callable[[Action], Action]

_actions: List[Type[Action]] = []


def no_wrapper(action: Action) -> Action:
    return action


def _register_action(cls: Type[Action]) -> Type[Action]:
    # Validate the action instance.
    if not issubclass(cls, Action):
        raise TypeError(f"Registered class {cls.__name__} must be a subclass of Action")

    _actions.append(cls)
    return cls


def kmd_action(cls: Type[Action]) -> Type[Action]:
    """
    Annotation to register an action.
    """
    return _register_action(cls)


def instantiate_actions() -> Dict[str, Action]:
    actions_map: Dict[str, Action] = {}
    for cls in _actions:
        action: Action = cls()  # type: ignore
        if action.name in actions_map:
            log.error(
                "%s Duplicate action name (defined twice by accident?): %s", EMOJI_WARN, action.name
            )
        actions_map[action.name] = action

    return dict(sorted(actions_map.items()))
