from kmd.config.logger import get_logger
from kmd.exec.action_registry import kmd_action
from kmd.model import LLM, LLMAction, Message, MessageTemplate
from kmd.text_docs.window_settings import WINDOW_256_PARA, WindowSettings


log = get_logger(__name__)


@kmd_action
class Proofread(LLMAction):
    name: str = "proofread"

    description: str = "Proofread text, only fixing spelling, punctuation, and grammar."

    system_message: Message = Message(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    )

    template: MessageTemplate = MessageTemplate(
        """
        Proofread the following text according to these rules:

        - Correct only typos or spelling, grammar, capitalization, or punctuation mistakes.

        - Write out only the final corrected text.

        - Preserve all Markdown formatting.

        - Make punctuation and capitalization changes to fit the Chicago Manual of Style.
          (For example, make sure we do not capitalize words unless they are proper nouns or
          at the start of a sentence.)

        - If input is a sentence or question without punctuation, be sure to add a period or
          question mark at the end, as appropriate.

        - Do not alter the meaning of any of the text or change the style of writing.

        - If unsure about how to make a correction, leave that portion of the text unchanged.
        
        - ONLY GIVE THE CORRECTED TEXT, with no other commentary. 

        Original text:
        
        {body}

        Corrected text:
        """
    )

    model: LLM = LLM.o1_mini

    windowing: WindowSettings = WINDOW_256_PARA
