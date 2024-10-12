from typing import Callable, Dict, List, Type

from kmd.config.logger import get_logger
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
    Decoration to register an action. This also ensures that the action is
    a Pydantic dataclass.
    """
    return _register_action(cls)

    # FIXME: Migrate all action defs and turn this on.
    # Apply Pydantic's @dataclass decorator if not already a Pydantic dataclass.
    # if not is_pydantic_dataclass(cls):
    #     pydantic_cls = cast(Type[Action], pydantic_dataclass(cls))
    # else:
    #     pydantic_cls = cast(Type[Action], cls)

    # return _register_action(pydantic_cls)


def instantiate_actions() -> Dict[str, Action]:
    actions_map: Dict[str, Action] = {}
    for cls in _actions:
        action: Action = cls()  # type: ignore
        if action.name in actions_map:
            log.error("Duplicate action name (defined twice by accident?): %s", action.name)
        actions_map[action.name] = action

    return dict(sorted(actions_map.items()))
