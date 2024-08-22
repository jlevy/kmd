from typing import Optional
from kmd.config.settings import DEFAULT_CAREFUL_MODEL
from kmd.exec.action_registry import kmd_action
from kmd.config.logger import get_logger
from kmd.exec.llm_transforms import llm_transform_item
from kmd.model.actions_model import TitleTemplate
from kmd.model.items_model import Item
from kmd.model.language_models import LLM
from kmd.model.llm_actions_model import CachedLLMAction
from kmd.model.llm_message_model import LLMMessage, LLMTemplate
from kmd.text_docs.sliding_transforms import WindowSettings
from kmd.text_docs.text_diffs import DiffFilterType

log = get_logger(__name__)


def define_llm_action(
    name: str,
    description: str,
    system_message: LLMMessage,
    template: LLMTemplate,
    model: LLM = DEFAULT_CAREFUL_MODEL,
    title_template: TitleTemplate = TitleTemplate("{title}"),
    windowing: Optional[WindowSettings] = None,
    diff_filter: Optional[DiffFilterType] = None,
    **kwargs,
):
    """
    Convenience method to register an LLM action.
    """

    @kmd_action
    class CustomLLMAction(CachedLLMAction):
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

        def run_item(self, item: Item) -> Item:
            return llm_transform_item(self, item)
