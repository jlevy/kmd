from kmd.model import Message, MessageTemplate, TitleTemplate, CachedLLMAction
from kmd.text_docs.window_settings import WINDOW_16_PARA
from kmd.exec.action_registry import kmd_action


@kmd_action()
class SummarizeAsBullets(CachedLLMAction):
    def __init__(self):
        super().__init__(
            name="summarize_as_bullets",
            description="Summarize text as bullet points.",
            system_message=Message(
                """
                You are a careful and precise editor.
                You give exactly the results requested without additional commentary.
                """
            ),
            title_template=TitleTemplate("Summary of {title}"),
            template=MessageTemplate(
                """
                Summarize the following text as a list of concise bullet points:

                - Each point should be one sentence long.
                
                - Include all key numbers or facts, without omitting any claims or important details.
                
                - Use simple and precise language.

                - Simply state the facts or claims without referencing the text or the author. For example, if the
                  text is about cheese being nutritious, you can say "Cheese is nutritious." But do NOT
                  say "The author says cheese is nutritious" or "According to the text, cheese is nutritious."

                - It is very important you do not add any details that are not directly stated in the original text.
                  Do not change any numbers or alter its meaning in any way.

                - Format your response as a list of bullet points in Markdown format.

                - Do NOT give any additional response at the beginning, such as "Here are the concise bullet points".
                  Simply give the summary.

                - If the input is very short or so unclear you can't summarize it, simply output "(No results)".

                Input text:

                {body}

                Bullet points:
                """
            ),
            windowing=WINDOW_16_PARA,
        )
