from kmd.config.settings import DEFAULT_FAST_MODEL
from kmd.exec.action_builders import define_llm_action
from kmd.config.logger import get_logger
from kmd.model.actions_model import LLMMessage, LLMTemplate
from kmd.text_docs.window_settings import WINDOW_1_PARA


log = get_logger(__name__)


define_llm_action(
    name="proofread",
    description="Proofread text, only fixing spelling, punctuation, and grammar.",
    model=DEFAULT_FAST_MODEL,
    system_message=LLMMessage(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    template=LLMTemplate(
        """
        You are a careful and precise editor. Proofread the following text according to these rules:

        - Correct only typos or spelling, grammar, capitalization, or punctuation mistakes.

        - Write out only the final corrected text.

        - Make punctuation and capitalization changes to fit the Chicago Manual of Style.

        - If input is a sentence or question without punctuation, be sure to add a period or
          question mark at the end, as appropriate.

        - Do not alter the meaning of any of the text or change the style of writing.

        - Do not capitalize words unless they are proper nouns or at the start of a sentence.

        - If unsure about any correction, leave that portion of the text unchanged.

        - Preserve all Markdown formatting.

        - If unsure about how to make a correction, leave that portion of the text unchanged.
        
        - ONLY GIVE THE CORRECTED TEXT, with no other commentary. 
        Original text:
        
        {body}

        Corrected text:
        """
    ),
    windowing=WINDOW_1_PARA,
)
