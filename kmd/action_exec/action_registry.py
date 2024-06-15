from typing import List, Type
from kmd.model.actions_model import Action
from kmd.config.logger import get_logger

log = get_logger(__name__)

_actions: List[Type[Action]] = []


def kmd_action(cls: Type[Action]):
    """
    Annotation to register an action.
    """
    # Validate the action instance.
    if not issubclass(cls, Action):
        raise TypeError(f"Registered class {cls.__name__} must be a subclass of Action")

    _actions.append(cls)
    return cls


def instantiate_actions() -> dict[str, Action]:
    actions_map = {}
    for cls in _actions:
        action: Action = cls()  # type: ignore
        actions_map[action.name] = action

    return dict(sorted(actions_map.items()))
