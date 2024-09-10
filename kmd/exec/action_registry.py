import inspect
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple, Type

from kmd.config.logger import get_logger
from kmd.config.text_styles import EMOJI_WARN
from kmd.model.actions_model import (
    Action,
    ActionInput,
    ActionResult,
    ANY_ARGS,
    ForEachItemAction,
    ONE_ARG,
)
from kmd.model.errors_model import ContentError
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

    @dataclass(frozen=True)
    class EachItemWrapper(ForEachItemAction, action.__class__):

        def __init__(self):
            # Bit of a hack: We don't know the subclass constructor args so dynamically get the ones we need.
            action_init_params = inspect.signature(action.__class__.__init__).parameters
            init_args = {
                param: getattr(action, param) for param in action_init_params if param != "self"
            }
            action.__class__.__init__(self, **init_args)
            ForEachItemAction.__init__(
                self,
                name=action.name,
                description=action.description,
                expected_args=ANY_ARGS,
                precondition=action.precondition,
            )

        def run(self, items: ActionInput) -> ActionResult:
            return super(ForEachItemAction, self).run(items)

        def run_item(self, item: Item) -> Item:
            result_items = action.run([item]).items
            if len(result_items) < 1:
                raise ContentError(f"Action `{action.name}` returned no items")
            return result_items[0]

    if action.expected_args != ONE_ARG:
        raise ValueError(f"Action `{action.name}` must expect exactly one argument")

    return EachItemWrapper()


def _register_action(cls: Type[Action], wrapper: ActionWrapper) -> Type[Action]:
    # Validate the action instance.
    if not issubclass(cls, Action):
        raise TypeError(f"Registered class {cls.__name__} must be a subclass of Action")

    _actions.append((cls, wrapper))
    return cls


def kmd_action(for_each_item: bool = False) -> Callable[[Type[Action]], Type[Action]]:
    """
    Annotation to register an action.

    If `for_each_item` is True, the action should accept a single item will be wrapped
    so that it runs on each input item for multiple inputs.
    """

    def decorator(cls: Type[Action]) -> Type[Action]:
        actual_wrapper = each_item_wrapper if for_each_item else no_wrapper
        return _register_action(cls, actual_wrapper)

    return decorator


def instantiate_actions() -> Dict[str, Action]:
    actions_map: Dict[str, Action] = {}
    for cls, wrapper in _actions:
        action: Action = wrapper(cls())  # type: ignore
        if action.name in actions_map:
            log.error(
                "%s Duplicate action name (defined twice by accident?): %s", EMOJI_WARN, action.name
            )
        actions_map[action.name] = action

    return dict(sorted(actions_map.items()))
