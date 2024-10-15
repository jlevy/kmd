import re
from typing import List

from kmd.docs import faq


def faq_headings() -> List[str]:
    """
    Questions from the FAQ text.
    """
    questions = re.findall(r"^#+ (.+\?)\s*$", str(faq), re.MULTILINE)  # type: ignore
    assert len(questions) > 2

    return [question.strip("# ") for question in questions]
