from textwrap import dedent
from typing import Generator
from pprint import pprint
from kmd.text_handling.text_doc import DocIndex, Paragraph, TextDoc, size, size_space


def seek_doc(doc: TextDoc, offset: int) -> DocIndex:
    """
    Find the last sentence that starts before a given offset in bytes.
    """
    current_size = 0
    last_fit_index = DocIndex(0, 0)

    for para_index, para in enumerate(doc.paragraphs):
        for sent_index, sent in enumerate(para.sentences):
            sentence_size = size(sent)
            if current_size + sentence_size + size_space <= offset:
                current_size += sentence_size + size_space
                last_fit_index = DocIndex(para_index, sent_index)
            else:
                return last_fit_index

    return last_fit_index


def sliding_window(
    doc: TextDoc, window_size: int = 16 * 1024, shift: int = 8 * 1024
) -> Generator[TextDoc, None, None]:
    """
    Generate TextDoc sub-documents in a sliding window over the given document.
    """
    total_size = doc.size()
    start_offset = 0
    start_index = seek_doc(doc, start_offset)

    while start_offset < total_size:
        end_offset = start_offset + window_size
        end_index = seek_doc(doc, end_offset)

        # Sentence may go over the window, so back up to ensure it fits.
        sub_doc = doc.sub_doc(start_index, end_index)
        try:
            while sub_doc.size() > window_size:
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

    offset = len("This is the first paragraph.")
    index = seek_doc(doc, offset)
    assert index == DocIndex(para_index=0, sent_index=0)

    offset = len(
        "This is the first paragraph. It has multiple sentences.\n\nThis is the second paragraph."
    )
    index = seek_doc(doc, offset)
    assert index == DocIndex(para_index=1, sent_index=0)

    offset = len(_example_text) + 10
    index = seek_doc(doc, offset)
    assert index == DocIndex(para_index=2, sent_index=2)


def test_sliding_window():
    doc = TextDoc.from_text(_example_text)
    window_size = 80
    shift = 60

    windows = list(sliding_window(doc, window_size, shift))

    assert windows == [
        TextDoc(
            paragraphs=[
                Paragraph(
                    original_text="This is the first paragraph. It has multiple sentences.",
                    sentences=["This is the first paragraph.", "It has multiple sentences."],
                )
            ]
        ),
        TextDoc(
            paragraphs=[
                Paragraph(
                    original_text="It has multiple sentences.",
                    sentences=["It has multiple sentences."],
                ),
                Paragraph(
                    original_text="This is the second paragraph.",
                    sentences=["This is the second paragraph."],
                ),
            ]
        ),
        TextDoc(
            paragraphs=[
                Paragraph(
                    original_text="This is the second paragraph. It also has multiple sentences. And it continues.",
                    sentences=[
                        "This is the second paragraph.",
                        "It also has multiple sentences.",
                        "And it continues.",
                    ],
                )
            ]
        ),
        TextDoc(
            paragraphs=[
                Paragraph(original_text="And it continues.", sentences=["And it continues."]),
                Paragraph(
                    original_text="Here is the third paragraph. " "More sentences follow.",
                    sentences=["Here is the third paragraph.", "More sentences follow."],
                ),
            ]
        ),
    ]

    for sub_doc in windows:
        sub_text = sub_doc.reassemble()

        print(f"\n\n---Sub-document length {size(sub_text)}")
        pprint(sub_text)

        assert size(sub_text) <= window_size

        assert sub_text in doc.reassemble()
