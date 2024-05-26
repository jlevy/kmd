from typing import Dict, Type

from cachetools import cached
from kmd.actions.llm_action_base import LLMAction
from kmd.model.actions_model import Action
from kmd.action_defs import import_all_actions
from kmd.config.logger import get_logger

log = get_logger(__name__)

_actions = []


def register_action(cls: Type[Action]):
    """
    Annotation to register an action.
    """
    # Validate the action instance.
    if not issubclass(cls, Action):
        raise TypeError(f"Registered class {cls.__name__} must be a subclass of Action")

    _actions.append(cls)
    return cls


def register_llm_action(
    name, friendly_name, description, model, system_message, title_template, template
):
    """
    Convenience method to register an LLM action.
    """

    @register_action
    class CustomLLMAction(LLMAction):
        def __init__(self):
            super().__init__(
                name,
                friendly_name,
                description,
                model=model,
                system_message=system_message,
                title_template=title_template,
                template=template,
            )

    return CustomLLMAction


@cached({})
def load_all_actions() -> Dict[str, Action]:
    import_all_actions()

    actions_map = {}
    for cls in _actions:
        action = cls()
        actions_map[action.name] = action

    actions_map = dict(sorted(actions_map.items()))
    log.info("Registered actions: %s", list(actions_map.keys()))
    return actions_map
