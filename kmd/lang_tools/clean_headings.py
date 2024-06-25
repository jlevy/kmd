from textwrap import dedent
from kmd.action_exec.llm_completion import llm_completion
from kmd.model.language_models import LLM


def clean_heading(heading: str) -> str:
    """
    Fast LLM call to edit and clean up a heading.
    """
    return llm_completion(
        LLM.groq_llama3_70b_8192.value,
        system_message="You are a careful and precise editor.",
        template=dedent(
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
    # FIXME: Enforce that the edit doesn't contain anything extraneous.
