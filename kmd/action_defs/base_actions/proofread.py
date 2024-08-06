from kmd.action_exec.action_builders import define_llm_action
from kmd.config.logger import get_logger
from kmd.model.actions_model import LLMMessage, LLMTemplate
from kmd.model.language_models import LLM
from kmd.text_docs.window_settings import WINDOW_1_PARA


log = get_logger(__name__)


define_llm_action(
    name="proofread",
    description="Proofread text, only fixing spelling, punctuation, and grammar.",
    model=LLM.gpt_3_5_turbo.value,
    system_message=LLMMessage(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    template=LLMTemplate(
        """
        Proofread the following text according to these rules:

        - Correct only typos or spelling, grammar, capitalization, or punctuation mistakes.

        - Write out only the final corrected text.

        - If input is a single phrase that looks like a question, be sure to add a question mark at the end.

        - Do not alter the meaning of any of the text or change the style of writing.

        - Do not capitalize words unless they are proper nouns or at the start of a sentence.

        - If unsure about any correction, leave that portion of the text unchanged.

        - Preserve all Markdown formatting.

        - ONLY GIVE THE CORRECTED TEXT, with no other commentary.
        
        Original text:
        
        {body}

        Corrected text:
        """
    ),
    windowing=WINDOW_1_PARA,
)
