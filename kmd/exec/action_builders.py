from typing import Optional
from kmd.exec.action_registry import kmd_action
from kmd.exec.llm_action_base import LLMAction
from kmd.config.logger import get_logger
from kmd.model.actions_model import LLMMessage, LLMTemplate, TitleTemplate
from kmd.model.language_models import LLM
from kmd.text_docs.sliding_transforms import WindowSettings
from kmd.text_docs.text_diffs import DiffOpFilter

log = get_logger(__name__)


def define_llm_action(
    name: str,
    description: str,
    model: LLM,
    system_message: LLMMessage,
    template: LLMTemplate,
    title_template: TitleTemplate = TitleTemplate("{title}"),
    windowing: Optional[WindowSettings] = None,
    diff_filter: Optional[DiffOpFilter] = None,
    **kwargs,
):
    """
    Convenience method to register an LLM action.
    """

    @kmd_action
    class CustomLLMAction(LLMAction):
        def __init__(self):
            super().__init__(
                name=name,
                description=description,
                model=model,
                system_message=system_message,
                title_template=title_template,
                template=template,
                windowing=windowing,
                diff_filter=diff_filter,
                **kwargs,
            )
