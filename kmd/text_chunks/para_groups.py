from typing import Callable, Generator, TypeVar
from kmd.text_docs.text_doc import TextDoc, TextUnit


T = TypeVar("T")


def chunk_generator(
    doc: T, condition: Callable[[T], bool], slicer: Callable[[T, int, int], T], total_size: int
) -> Generator[T, None, None]:
    """
    Walk through the elements of a document and yield sequential subdocs once they meet
    a specific condition.
    """

    start_index = 0
    current_index = 0

    while current_index < total_size:
        current_doc = slicer(doc, start_index, current_index)

        if condition(current_doc):
            yield current_doc
            start_index = current_index + 1
            current_index = start_index
        else:
            current_index += 1

    if start_index < total_size:
        yield slicer(doc, start_index, total_size)


def text_doc_chunk_paras(
    doc: TextDoc, min_size: int, unit: TextUnit
) -> Generator[TextDoc, None, None]:
    """
    Generate TextDoc chunks where each chunk is at least the specified minimum size.
    """
    condition = lambda subdoc: subdoc.size(unit) >= min_size
    total_paragraphs = len(doc.paragraphs)
    slicer = lambda d, start, end: d.sub_paras(start, end)

    for chunk in chunk_generator(doc, condition, slicer, total_paragraphs):
        yield chunk
