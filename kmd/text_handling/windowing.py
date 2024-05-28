from textwrap import dedent
from typing import Callable, Generator
from pprint import pprint
from kmd.config.logger import get_logger
from kmd.text_handling.text_doc import (
    DocIndex,
    TextDoc,
    Unit,
    size,
    size_in_bytes,
)
from kmd.text_handling.text_tokens import PARA_BR_STR, SENT_BR_STR


log = get_logger(__name__)


def seek_doc(doc: TextDoc, offset: int, unit: Unit) -> DocIndex:
    """
    Find the last sentence that starts before a given offset in bytes.
    """
    current_size = 0
    last_fit_index = DocIndex(0, 0)

    if unit == Unit.BYTES:
        size_sent_break = size_in_bytes(SENT_BR_STR)
        size_para_break = size_in_bytes(PARA_BR_STR)
    elif unit == Unit.TOKENS:
        size_sent_break = 1
        size_para_break = 1
    else:
        raise ValueError(f"Invalid unit {unit}")

    for para_index, para in enumerate(doc.paragraphs):
        for sent_index, sent in enumerate(para.sentences):
            sentence_size = sent.size(unit)
            last_fit_index = DocIndex(para_index, sent_index)
            if current_size + sentence_size + size_sent_break <= offset:
                current_size += sentence_size
                if sent_index < len(para.sentences) - 1:
                    current_size += size_sent_break
            else:
                return last_fit_index
        if para_index < len(doc.paragraphs) - 1:
            current_size += size_para_break

    return last_fit_index


def sliding_window(
    doc: TextDoc, window_size: int, shift: int, unit: Unit
) -> Generator[TextDoc, None, None]:
    """
    Generate TextDoc sub-documents in a sliding window over the given document.
    """
    total_size = doc.size(unit)
    start_offset = 0
    start_index = seek_doc(doc, start_offset, unit)

    while start_offset < total_size:
        end_offset = start_offset + window_size
        end_index = seek_doc(doc, end_offset, unit)

        # Sentence may extend past the window, so back up to ensure it fits.
        sub_doc = doc.sub_doc(start_index, end_index)
        try:
            while sub_doc.size(unit) > window_size:
                end_index = doc.prev_sent(end_index)
                sub_doc = doc.sub_doc(start_index, end_index)
        except ValueError:
            raise ValueError(
                f"Window size {window_size} too small for sentence at offset {start_offset}"
            )

        yield sub_doc

        start_offset += shift
        start_index = end_index


## Tests

_example_text = dedent(
    """
    This is the first paragraph. It has multiple sentences.

    This is the second paragraph. It also has multiple sentences. And it continues.
    
    Here is the third paragraph. More sentences follow. And here is another one.
    """
).strip()


def test_seek_doc():
    doc = TextDoc.from_text(_example_text)

    offset = 1
    index = seek_doc(doc, offset, Unit.BYTES)
    print(f"Seeked to {index} for offset {offset} bytes")
    assert index == DocIndex(para_index=0, sent_index=0)

    offset = len("This is the first paragraph.")
    index = seek_doc(doc, offset, Unit.BYTES)
    print(f"Seeked to {index} for offset {offset} bytes")
    assert index == DocIndex(para_index=0, sent_index=0)

    offset = len("This is the first paragraph. ")
    index = seek_doc(doc, offset, Unit.BYTES)
    print(f"Seeked to {index} for offset {offset} bytes")
    assert index == DocIndex(para_index=0, sent_index=1)

    offset = len(
        "This is the first paragraph. It has multiple sentences.\n\nThis is the second paragraph."
    )
    index = seek_doc(doc, offset, Unit.BYTES)
    print(f"Seeked to {index} for offset {offset} bytes")
    assert index == DocIndex(para_index=1, sent_index=0)

    offset = len(_example_text) + 10
    index = seek_doc(doc, offset, Unit.BYTES)
    print(f"Seeked to {index} for offset {offset} bytes")
    assert index == DocIndex(para_index=2, sent_index=2)


def test_sliding_window():
    doc = TextDoc.from_text(_example_text)
    window_size = 80
    shift = 60

    windows = list(sliding_window(doc, window_size, shift, Unit.BYTES))
    pprint(windows)

    sentence_windows = [
        [[sent.text for sent in para.sentences] for para in doc.paragraphs] for doc in windows
    ]

    assert sentence_windows == [
        [["This is the first paragraph.", "It has multiple sentences."]],
        [["It has multiple sentences."], ["This is the second paragraph."]],
        [["This is the second paragraph.", "It also has multiple sentences.", "And it continues."]],
        [["And it continues."], ["Here is the third paragraph.", "More sentences follow."]],
    ]

    for sub_doc in windows:
        sub_text = sub_doc.reassemble()

        print(f"\n\n---Sub-document length {size(sub_text, Unit.BYTES)}")
        pprint(sub_text)

        assert size(sub_text, Unit.BYTES) <= window_size

        assert sub_text in doc.reassemble()
