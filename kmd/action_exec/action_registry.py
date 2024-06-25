from typing import List, Type, Tuple, Optional, Callable
from kmd.model.actions_model import ANY_ARGS, ONE_ARG, Action, EachItemAction
from kmd.config.logger import get_logger
from kmd.model.items_model import Item

log = get_logger(__name__)

ActionWrapper = Callable[[Action], Action]

_actions: List[Tuple[Type[Action], ActionWrapper]] = []


def no_wrapper(action: Action) -> Action:
    return action


def each_item_wrapper(action: Action) -> Action:
    """
    Wrap an action that runs on a single item as one that that processes all input items.
    """

    class EachItemWrapper(EachItemAction):
        def run_item(self, item: Item) -> Item:
            return action.run([item]).items[0]

    if action.expected_args != ONE_ARG:
        raise ValueError(f"Action {action.name} must expect exactly one argument")

    return EachItemWrapper(
        name=action.name,
        friendly_name=action.friendly_name,
        description=action.description,
        expected_args=ANY_ARGS,
    )


def _register_action(cls: Type[Action], wrapper: ActionWrapper) -> Type[Action]:
    # Validate the action instance.
    if not issubclass(cls, Action):
        raise TypeError(f"Registered class {cls.__name__} must be a subclass of Action")

    _actions.append((cls, wrapper))
    return cls


def kmd_action(cls: Type[Action]) -> Type[Action]:
    """
    Annotation to register an action.
    """
    return _register_action(cls, no_wrapper)


def kmd_action_wrapped(wrapper: ActionWrapper) -> Callable[[Type[Action]], Type[Action]]:
    """
    Annotation to register an action, also wrapping it with additional functionality.
    """

    def decorator(cls: Type[Action]) -> Type[Action]:
        return _register_action(cls, wrapper)

    return decorator


def instantiate_actions() -> dict[str, Action]:
    actions_map = {}
    for cls, wrapper in _actions:
        action: Action = wrapper(cls())  # type: ignore
        actions_map[action.name] = action

    return dict(sorted(actions_map.items()))
