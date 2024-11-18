from kmd.exec.action_registry import kmd_action
from kmd.model import LLMAction, Message, MessageTemplate, TitleTemplate
from kmd.text_docs.window_settings import WINDOW_128_PARA, WindowSettings


@kmd_action
class SummarizeAsBullets(LLMAction):

    name: str = "summarize_as_bullets"

    description: str = """
        Summarize text as bullet points.
        """

    system_message: Message = Message(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    )

    title_template: TitleTemplate = TitleTemplate("Summary of {title}")

    template: MessageTemplate = MessageTemplate(
        """
        Summarize the following text as a list of concise bullet points:

        - Each point should be one sentence long.

        - Format your response as a list of bullet points in Markdown format.

        - Do NOT use nested bullet points. Give a single list, not a list of lists.
        
        - Include all key numbers or facts, without omitting any claims or important details.
        
        - Use simple and precise language.

        - Simply state the facts or claims without referencing the text or the author. For example, if the
          text is about cheese being nutritious, you can say "Cheese is nutritious." But do NOT
          say "The author says cheese is nutritious" or "According to the text, cheese is nutritious."

        - It is very important you do not add any details that are not directly stated in the original text.
          Do not change any numbers or alter its meaning in any way.

        - Do NOT give any additional response at the beginning, such as "Here are the concise bullet points".
          Simply give the summary.

        - If the input is very short or so unclear you can't summarize it, simply output "(No results)".

        Input text:

        {body}

        Bullet points:
        """
    )

    windowing: WindowSettings = WINDOW_128_PARA
