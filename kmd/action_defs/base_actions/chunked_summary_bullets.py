from kmd.config.settings import DEFAULT_CAREFUL_MODEL
from kmd.exec.llm_action_base import ChunkedLLMAction
from kmd.model.actions_model import LLMMessage, LLMTemplate
from kmd.model.html_conventions import ORIGINAL, SUMMARY
from kmd.model.language_models import LLM
from kmd.exec.action_registry import kmd_action


@kmd_action
class ChunkedSummaryBullets(ChunkedLLMAction):
    def __init__(self):
        super().__init__(
            name="chunked_summary_bullets",
            description="Summarize text as bullet points.",
            model=DEFAULT_CAREFUL_MODEL,
            result_class_name=SUMMARY,
            original_class_name=ORIGINAL,
            system_message=LLMMessage(
                """
                You are a careful and precise editor.
                You give exactly the results requested without additional commentary.
                """
            ),
            template=LLMTemplate(
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

                - If the input is very short or so unclear you can't summarize it, simply output "(No summary available)".

                Input text:

                {body}

                Bullet points:
                """
            ),
        )
