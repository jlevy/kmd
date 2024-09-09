from kmd.config.logger import get_logger
from kmd.model.actions_model import Message, MessageTemplate
from kmd.config.settings import DEFAULT_FAST_MODEL
from kmd.text_docs.text_diffs import DiffFilterType
from kmd.text_docs.window_settings import WINDOW_2K_WORDTOKS
from kmd.model.llm_actions_model import CachedLLMAction
from kmd.exec.action_registry import kmd_action


log = get_logger(__name__)


@kmd_action()
class BreakIntoParagraphs(CachedLLMAction):
    def __init__(self):
        super().__init__(
            name="break_into_paragraphs",
            description="Reformat text as paragraphs.",
            model=DEFAULT_FAST_MODEL,
            system_message=Message(
                """
                You are a careful and precise editor.
                You give exactly the results requested without additional commentary.
                """
            ),
            template=MessageTemplate(
                """
                Format this text according to these rules:

                - Break the following text into paragraphs so it is readable and organized.

                - Add a paragraph break whenever the topic changes.

                - Paragraphs can be short or up to several sentences long.

                - Do *not* change any words of the text. Add line breaks only.

                - Preserve all Markdown formatting.

                - ONLY GIVE THE FORMATTED TEXT, with no other commentary.

                Original text:

                {body}

                Formatted text:
                """
            ),
            windowing=WINDOW_2K_WORDTOKS,
            diff_filter=DiffFilterType.only_breaks_and_spaces,
        )
