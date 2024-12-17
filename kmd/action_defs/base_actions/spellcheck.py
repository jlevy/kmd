from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import LLM, LLMAction, Message, MessageTemplate
from kmd.text_docs.window_settings import WINDOW_128_PARA, WindowSettings


log = get_logger(__name__)

# FIXME: Get this working cleanly with highly formatted Markdown like
# a project readme.


@kmd_action
class Spellcheck(LLMAction):
    name: str = "spellcheck"

    description: str = """
        Spellcheck text, only fixing spelling, punctuation, and capitalization.
        """

    system_message: Message = Message(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    )

    template: MessageTemplate = MessageTemplate(
        """
        Spell check the following text according to these rules:

        - Correct *ONLY* spelling, capitalization, and punctuation.

        - Write out only the final corrected text.

        - Preserve all Markdown formatting.

        - Make punctuation and capitalization changes to fit the Chicago Manual of Style.
          (For example, make sure we do not capitalize words unless they are proper nouns or
          at the start of a sentence.)

        - If unsure about how to make a correction, leave that portion of the text unchanged.
        
        - ONLY GIVE THE CORRECTED TEXT, with no other commentary. 

        Original text:
        
        {body}

        Corrected text:
        """
    )

    model: LLM = LLM.groq_llama_3_1_8b_instant

    windowing: WindowSettings = WINDOW_128_PARA
