from typing import List
from kmd.llms.llm_completion import llm_completion
from kmd.model.actions_model import LLMMessage, LLMTemplate
from kmd.model.language_models import LLM
from kmd.text_formatting.markdown_util import as_bullet_points

# TODO: Enforce that the edits below doesn't contain anything extraneous.


def clean_heading(heading: str) -> str:
    """
    Fast LLM call to edit and clean up a heading.
    """
    return llm_completion(
        LLM.groq_llama3_70b_8192.value,
        system_message=LLMMessage(
            """
            You are a careful and precise editor. You follow directions exactly and do not embellish or offer any other commentary.
            """
        ),
        template=LLMTemplate(
            """
            Edit the following heading to be suitable for a title of a web page or section in a document.
            Follow Chicago Manual of Style capitalizaiton rules. Remove any ellipses, bracketed words or
            parentheticals, word fragments, extraneous words or punctuationmat the end such as
            "…" or "..." or "(edited)" or "(full text) (transcription)".

            Output ONLY the edited heading, with no other text.

            Original heading: {body}

            Edited heading:
            """
        ),
        input=heading,
        save_objects=False,
    )


def summary_heading(values: List[str]) -> str:

    return llm_completion(
        LLM.groq_llama3_70b_8192.value,
        system_message=LLMMessage(
            """
            You are a careful and precise editor. You follow directions exactly and do not embellish or offer any other commentary.
            """
        ),
        template=LLMTemplate(
            """
            Summarize the following list of headings into a single heading that captures the essence of the list.
            Follow Chicago Manual of Style capitalization rules. Remove any ellipses, bracketed words or
            parentheticals, word fragments, extraneous words or punctuation at the end such as
            "…" or "..." or "(edited)" or "(transcribe)" or "(full text) (transcription)".

            Output ONLY the edited heading, with no other text.

            Headings:
            
            {body}

            Summarized heading:
            """
        ),
        input=as_bullet_points(values),
        save_objects=False,
    )
