from typing import Callable, Generator
from kmd.text_docs.text_doc import TextDoc, TextUnit


def para_groups(
    doc: TextDoc, condition: Callable[[TextDoc], bool]
) -> Generator[TextDoc, None, None]:
    """
    Walk through the paragraphs of a TextDoc and yield sequential subdocs once they meet
    a specific condition.
    """

    start_index = 0
    current_index = 0
    total_paragraphs = len(doc.paragraphs)

    while current_index < total_paragraphs:
        current_doc = doc.sub_paras(start_index, current_index)

        if condition(current_doc):
            yield current_doc
            start_index = current_index + 1
            current_index = start_index
        else:
            current_index += 1

    if start_index < total_paragraphs:
        yield doc.sub_paras(start_index)


def para_groups_by_size(
    doc: TextDoc, min_size: int, unit: TextUnit
) -> Generator[TextDoc, None, None]:
    """
    Generate TextDoc chunks where each chunk is at least the specified minimum size.
    """
    condition = lambda subdoc: subdoc.size(unit) >= min_size

    for chunk in para_groups(doc, condition):
        yield chunk
