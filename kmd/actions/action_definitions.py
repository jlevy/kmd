from textwrap import dedent
from kmd.actions.action_lib import ActionInput, ActionResult, CrawlAction
from kmd.actions.llm_actions import LLM, LLMAction
from kmd.actions.registry import register_action


@register_action
def fetch_page(items: ActionInput) -> ActionResult:
    return CrawlAction().run(items)


@register_action
def proofread(items: ActionInput) -> ActionResult:
    return LLMAction(
        name="Proofread and Correct",
        description="Proofread text, only fixing spelling, punctuation, and grammar.",
        model=LLM.gpt_3_5_turbo_16k_0613.value,
        system_message=dedent(
            """
            You are a careful and precise editor.
            You give exactly the results requested without additional commentary.
            """
        ),
        title_template="{title} (proofread)",
        template=dedent(
            """
            Proofread the following text according to these rules:
            - Correct only typos or spelling, grammar, capitalization, or punctuation mistakes,
            - Write out only the final corrected text.
            - If input is a single phrase that looks like a question, be sure to add a question mark at the end.
            - Do not alter the meaning of any of the text or change the style of writing.
            - Do not capitalize words unless they are proper nouns or at the start of a sentence.
            - If unsure about any correction, leave that portion of the text unchanged.
            - Preserve all Markdown formatting.
            
            Input text:
            
            {body}

            Corrected text:
            """
        ),
    ).run(items[0])


@register_action
def break_into_paragraphs(items: ActionInput) -> ActionResult:
    return LLMAction(
        name="Break into Paragraphs",
        description="Reformat text as paragraphs.",
        model=LLM.gpt_3_5_turbo_16k_0613.value,
        system_message=dedent(
            """
            You are a careful and precise editor.
            You give exactly the results requested without additional commentary.
            """
        ),
        title_template="{title} (in paragraphs)",
        template=dedent(
            """
            Format this text according to these rules:
            - Break the following text into paragraphs so it is readable and organized.
            - Add oriented quotation marks so quotes are “like this” and not "like this".
            - Make any other punctuation changes to fit the Chicago Manual of Style.
            - Do *not* change any words of the text. Add line breaks and punctuation and formatting changes only.
            - Preserve all Markdown formatting.

            Input text:

            {body}

            Formatted text:
            """
        ),
    ).run(items[0])


@register_action
def summarize_as_bullets(items: ActionInput) -> ActionResult:
    return LLMAction(
        name="Summarize as Bullet Points",
        description="Summarize text as bullet points.",
        model=LLM.gpt_3_5_turbo_16k_0613.value,
        system_message=dedent(
            """
            You are a careful and precise editor.
            You give exactly the results requested without additional commentary.
            """
        ),
        title_template="Summary of {title}",
        template=dedent(
            """
            Summarize the following text as a list of concise bullet points, each one or two sentences long.
            Include all key numbers or facts, without omitting any key details.
            Use simple and precise language.
            It is very important you do not add any details that are not directly stated in the original text.
            Do not change any numbers or alter its meaning in any way.

            Input text:

            {body}

            Bullet points:
            """
        ),
    ).run(items[0])


@register_action
def extract_concepts(items: ActionInput) -> ActionResult:
    return LLMAction(
        name="Extract Concepts",
        description="Extract key concepts from text.",
        model=LLM.gpt_3_5_turbo_16k_0613.value,
        system_message=dedent(
            """
            You are a careful and precise editor.
            You give exactly the results requested without additional commentary.
            """
        ),
        title_template="Concepts from {title}",
        template=dedent(
            """
            You are collecting concepts for the glossary of a book.
            Identify and list any concepts from the following text
            Only include unusual or technical terms or names of companies or people.
            Do not include common concepts or general ideas.
            Each concept should be a single word or noun phrase.
            Write them as an itemized list of bullet points in Markdown format, with each word or
            phrase in Title Case.

            Input text:

            {body}

            Concepts:
            """
        ),
    ).run(items[0])
