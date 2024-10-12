from kmd.exec.action_registry import kmd_action
from kmd.model import LLMAction, Message, MessageTemplate, TitleTemplate
from kmd.text_docs.window_settings import WINDOW_128_PARA, WindowSettings


@kmd_action
class OutlineSectionHeadings(LLMAction):
    name: str = "outline_section_headings"

    description: str = "Outline a text as a list of section headings."

    system_message: Message = Message(
        """
                You are a careful and precise editor.
                You give exactly the results requested without additional commentary.
        """
    )

    title_template: TitleTemplate = TitleTemplate("Outline of {title}")

    template: MessageTemplate = MessageTemplate(
        """
                Give an outline of everything covered in the following text.

                - Format your response as a list of bullet points in Markdown format.

                - Each item should be in the style of a section heading for what is covered, in a form that
                  could work as a section heading in a table of contents.

                - Do NOT use nested bullet points. Give a single list, not a list of lists.

                - Add a heading every time topics change. The entire list should be an understandable
                  and representative outline of what was covered in the text.
                                
                - Section headings should be concise and specific. For example, use
                  "Importance of Sleep" and not just "Sleep", or "Reflections on Johanna's Early Childhood" and
                  not just "Childhood".
                 
                - Do NOT give any additional response at the beginning, such as "Here are the outline".
                  Simply give the summary.

                - If the input is very short or so unclear you can't outline it, simply output "(No results)".

                Input text:

                {body}

                Outline:
                """
    )

    windowing: WindowSettings = WINDOW_128_PARA
