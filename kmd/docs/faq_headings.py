import re
from typing import List
from kmd.docs.topics.faq import __doc__ as faq_doc


def faq_headings() -> List[str]:
    """
    Questions from the FAQ text.
    """
    questions = re.findall(r"^#+ (.+\?)\s*$", faq_doc, re.MULTILINE)  # type: ignore
    assert len(questions) > 2

    return [question.strip("# ") for question in questions]
