from textwrap import dedent
from typing import List
from kmd.actions.actions import Action, run_action
from kmd.actions.models import LLM
from kmd.actions.registry import register_action
from kmd.model.items import Item


@register_action
def proofread(items: List[Item]) -> Item:
    item = items[0]
    return run_action(
        Action(
            name="Edit: Proofread and Correct",
            description="Proofread text, only fixing spelling, punctuation, and grammar.",
            model=LLM.gpt_3_5_turbo_16k_0613,
            system_message=dedent(
                """
                You are a careful and precise editor.
                You give exactly the results requested without additional commentary.
                """
            ),
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
        ),
        item,
    )


@register_action
def break_into_paragraphs(items: List[Item]) -> Item:
    item = items[0]
    return run_action(
        Action(
            name="Edit: Break into Paragraphs",
            description="Reformat text as paragraphs.",
            model=LLM.gpt_3_5_turbo_16k_0613,
            system_message=dedent(
                """
                You are a careful and precise editor.
                You give exactly the results requested without additional commentary.
                """
            ),
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
        ),
        item,  # Add the missing argument "item"
    )


@register_action
def summarize_as_bullets(items: List[Item]) -> Item:
    item = items[0]
    return run_action(
        Action(
            name="Summarize: Bullet Points",
            description="Summarize text as bullet points.",
            model=LLM.gpt_3_5_turbo_16k_0613,
            system_message=dedent(
                """
                You are a careful and precise editor.
                You give exactly the results requested without additional commentary.
                """
            ),
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
        ),
        item,
    )
