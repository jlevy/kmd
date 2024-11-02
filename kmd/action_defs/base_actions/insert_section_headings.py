from kmd.exec.action_registry import kmd_action
from kmd.model import LLMAction, Message, MessageTemplate
from kmd.text_docs.diff_filters import adds_headings
from kmd.text_docs.token_diffs import DiffFilter
from kmd.text_docs.window_settings import WINDOW_128_PARA, WindowSettings


@kmd_action
class InsertSectionHeadings(LLMAction):

    name: str = "insert_section_headings"

    description: str = "Insert headings into a text as <h2> tags."

    system_message: Message = Message(
        """
                You are a careful and precise editor.
                You give exactly the results requested without additional commentary.
                """
    )

    template: MessageTemplate = MessageTemplate(
        """
        Insert headings into the following text using <h2> tags. 

        - Add a heading every time topics change, typically after 3-6 paragraphs, but follow your
          best judgement in terms of when the change in topic occurs.

        - Each heading should describe what is covered by the paragraphs that follow.

        - DO NOT change any text other than to add headings, each on its own line, in
          between the paragraphs of the text.
                        
        - Section headings should be concise and specific. For example, use
          "Importance of Sleep" and not just "Sleep", or "Reflections on Johanna's Early Childhood" and
          not just "Childhood".
          
        - Do NOT give any introductory response at the beginning, such as "Here is the text
          with headings added".

        - If the input is short, you can add a single heading at the beginning.

        - If the input is very short or unclear, output the text exactly, without adding any headings.

        Input text:

        {body}

        Output text (identical to input, but with headings added):
        """
    )

    windowing: WindowSettings = WINDOW_128_PARA

    diff_filter: DiffFilter = adds_headings
