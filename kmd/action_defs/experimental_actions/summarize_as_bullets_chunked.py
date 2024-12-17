from kmd.exec.action_registry import kmd_action
from kmd.exec.llm_transforms import llm_transform_str
from kmd.model import ChunkedLLMAction, Message, MessageTemplate, SUMMARY
from kmd.text_chunks.div_elements import div, div_get_original, div_insert_wrapped
from kmd.text_chunks.parse_divs import TextNode
from kmd.text_wrap.markdown_normalization import normalize_markdown


@kmd_action
class SummarizeAsBulletsChunked(ChunkedLLMAction):

    name: str = "summarize_as_bullets_chunked"

    description: str = """
        Summarize text as bullet points. Processes each div chunk.
        """

    system_message: Message = Message(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    )

    template: MessageTemplate = MessageTemplate(
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
    )

    def process_chunk(self, chunk: TextNode) -> str:
        transform_input = div_get_original(chunk)
        llm_response = normalize_markdown(llm_transform_str(self.context(), transform_input))
        new_div = div(SUMMARY, llm_response)

        return div_insert_wrapped(chunk, [new_div])
