import inspect
from pathlib import Path
from typing import Callable, cast, Dict, List, Optional, Type

from pydantic.dataclasses import dataclass as pydantic_dataclass, is_pydantic_dataclass

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
    a Pydantic dataclass and records the source path in `__source_path__`.
    """
    source_path: Optional[Path] = None
    try:
        if source_file := inspect.getsourcefile(cls):
            source_path = Path(source_file).resolve()
    except TypeError:
        pass

    # Apply Pydantic's @dataclass decorator if not already a Pydantic dataclass.
    if not is_pydantic_dataclass(cls):
        pydantic_cls = cast(Type[Action], pydantic_dataclass(cls))
    else:
        pydantic_cls = cast(Type[Action], cls)

    setattr(pydantic_cls, "__source_path__", source_path)

    return _register_action(pydantic_cls)


def instantiate_actions() -> Dict[str, Action]:
    actions_map: Dict[str, Action] = {}
    for cls in _actions:
        action: Action = cls()  # type: ignore
        if action.name in actions_map:
            log.error("Duplicate action name (defined twice by accident?): %s", action.name)

        # Record the source path.
        setattr(action, "__source_path__", getattr(cls, "__source_path__", None))

        actions_map[action.name] = action

    return dict(sorted(actions_map.items()))
