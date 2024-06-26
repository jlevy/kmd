from kmd.action_exec.action_registry import kmd_action
from kmd.action_exec.llm_action_base import LLMAction
from kmd.config.logger import get_logger

log = get_logger(__name__)


def define_llm_action(
    name,
    description,
    model,
    system_message,
    title_template,
    template,
    friendly_name=None,
    windowing=None,
    diff_filter=None,
):
    """
    Convenience method to register an LLM action.
    """

    @kmd_action
    class CustomLLMAction(LLMAction):
        def __init__(self):
            super().__init__(
                name,
                description,
                model=model,
                system_message=system_message,
                title_template=title_template,
                template=template,
                friendly_name=friendly_name,
                windowing=windowing,
                diff_filter=diff_filter,
            )
