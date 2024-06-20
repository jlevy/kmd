from kmd.action_exec.action_registry import kmd_action
from kmd.action_exec.llm_action_base import LLMAction
from kmd.config.logger import get_logger

log = get_logger(__name__)


def define_llm_action(
    name,
    friendly_name,
    description,
    model,
    system_message,
    title_template,
    template,
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
                friendly_name,
                description,
                model=model,
                system_message=system_message,
                title_template=title_template,
                template=template,
                windowing=windowing,
                diff_filter=diff_filter,
            )
