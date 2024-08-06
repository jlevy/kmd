from kmd.exec.action_builders import define_llm_action
from kmd.config.logger import get_logger
from kmd.model.actions_model import LLMMessage, LLMTemplate
from kmd.model.language_models import LLM
from kmd.text_docs.text_diffs import ONLY_BREAKS_AND_SPACES
from kmd.text_docs.window_settings import WINDOW_2K_WORDTOKS


log = get_logger(__name__)


define_llm_action(
    name="break_into_paragraphs",
    description="Reformat text as paragraphs.",
    model=LLM.groq_llama3_70b_8192.value,
    system_message=LLMMessage(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    template=LLMTemplate(
        """
        Format this text according to these rules:

        - Break the following text into paragraphs so it is readable and organized.

        - Add oriented quotation marks so quotes are “like this” and not "like this".

        - Make any other punctuation changes to fit the Chicago Manual of Style.

        - Do *not* change any words of the text. Add line breaks and punctuation and formatting changes only.

        - Preserve all Markdown formatting.

        - ONLY GIVE THE FORMATTED TEXT, with no other commentary.

        Original text:

        {body}

        Formatted text:
        """
    ),
    windowing=WINDOW_2K_WORDTOKS,
    diff_filter=ONLY_BREAKS_AND_SPACES,
)
