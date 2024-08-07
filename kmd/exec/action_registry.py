from typing import List, Type, Tuple, Callable
from kmd.model.actions_model import ANY_ARGS, ONE_ARG, Action, EachItemAction
from kmd.config.logger import get_logger
from kmd.model.errors_model import ContentError
from kmd.model.items_model import Item
from kmd.config.text_styles import EMOJI_WARN

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
            result_items = action.run([item]).items
            if len(result_items) < 1:
                raise ContentError(f"Action {action.name} returned no items")
            return result_items[0]

    if action.expected_args != ONE_ARG:
        raise ValueError(f"Action {action.name} must expect exactly one argument")

    return EachItemWrapper(
        name=action.name,
        description=action.description,
        expected_args=ANY_ARGS,
        precondition=action.precondition,
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
        if action.name in actions_map:
            log.error(
                "%s Duplicate action name (defined twice by accident?): %s", EMOJI_WARN, action.name
            )
        actions_map[action.name] = action

    return dict(sorted(actions_map.items()))
