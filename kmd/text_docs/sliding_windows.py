"""
Sliding windows of text on a text doc.
"""

from textwrap import dedent
from typing import Generator, Optional
from pprint import pprint
from kmd.config.logger import get_logger
from kmd.model.errors_model import ContentError
from kmd.model.items_model import Format
from kmd.text_formatting.doc_formatting import normalize_formatting
from kmd.text_docs.text_doc import (
    SentIndex,
    Sentence,
    TextDoc,
    Unit,
    size,
)
from kmd.text_docs.wordtoks import (
    join_wordtoks,
    raw_text_to_wordtoks,
)


log = get_logger(__name__)


def _truncate_sent_at_wordtok_offset(sent: Sentence, offset: int) -> Sentence:
    """
    Truncate a sentence to the given number of wordtoks.
    """
    wordtoks = raw_text_to_wordtoks(sent.text)
    truncated_wordtoks = wordtoks[:offset]
    joined = join_wordtoks(truncated_wordtoks)
    return Sentence(joined, sent.char_offset)


def truncate_at_wordtok_offset(doc: TextDoc, offset: int) -> TextDoc:
    """
    Truncate a document at a given wordtok offset.
    """
    index, _ = doc.seek_to_sent(offset, Unit.WORDTOKS)
    try:
        sub_doc = doc.sub_doc(SentIndex(0, 0), doc.prev_sent(index))
    except ValueError:
        # Offset is within the first sentence.
        sub_doc = TextDoc([])
    current_size = sub_doc.size(Unit.WORDTOKS)
    last_sent = doc.paragraphs[index.para_index].sentences[index.sent_index]
    remaining_wordtoks = offset - current_size - 1
    if remaining_wordtoks > 0:
        truncated_sent = _truncate_sent_at_wordtok_offset(last_sent, remaining_wordtoks)
        sub_doc.append_sent(truncated_sent)
    return sub_doc


def sliding_word_window(
    doc: TextDoc, window_size: int, window_shift: int, unit: Unit
) -> Generator[TextDoc, None, None]:
    """
    Generate TextDoc sub-documents in a sliding window over the given document.
    """
    total_size = doc.size(unit)
    start_offset = 0
    start_index, _ = doc.seek_to_sent(start_offset, unit)

    while start_offset < total_size:
        end_offset = start_offset + window_size
        end_index, _ = doc.seek_to_sent(end_offset, unit)

        # Sentence may extend past the window, so back up to ensure it fits.
        sub_doc = doc.sub_doc(start_index, end_index)
        try:
            while sub_doc.size(unit) > window_size:
                end_index = doc.prev_sent(end_index)
                sub_doc = doc.sub_doc(start_index, end_index)
        except ValueError:
            raise ContentError(
                f"Window size {window_size} too small for sentence at offset {start_offset}"
            )

        yield sub_doc

        start_offset += window_shift
        start_index = end_index


def sliding_para_window(
    doc: TextDoc, nparas: int, format: Optional[Format]
) -> Generator[TextDoc, None, None]:
    """
    Generate TextDoc sub-documents taking `nparas` paragraphs at a time.
    """
    for i in range(0, len(doc.paragraphs), nparas):
        end_index = min(i + nparas - 1, len(doc.paragraphs) - 1)
        sub_doc = doc.sub_doc(SentIndex(i, 0), SentIndex(end_index, 0))
        # XXX It's important we re-normalize especially because LLMs like itemized lists with just
        # one newline, but we want separate paragraphs for each list item.
        formatted_sub_doc = TextDoc.from_text(normalize_formatting(sub_doc.reassemble(), format))
        yield formatted_sub_doc


## Tests

_example_text = dedent(
    """
    This is the first paragraph. It has multiple sentences.

    This is the second paragraph. It also has multiple sentences. And it continues.
    
    Here is the third paragraph. More sentences follow. And here is another one.
    """
).strip()


def test_sliding_window():
    doc = TextDoc.from_text(_example_text)
    window_size = 80
    window_shift = 60

    windows = list(sliding_word_window(doc, window_size, window_shift, Unit.BYTES))
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


def test_truncate_at_wordtok():
    # Sentence truncation.
    sent = Sentence("This is a test sentence.", 999)
    truncated_sent = _truncate_sent_at_wordtok_offset(sent, 0)
    assert truncated_sent.text == ""

    truncated_sent = _truncate_sent_at_wordtok_offset(sent, 7)
    assert truncated_sent.text == "This is a test"
    assert truncated_sent.char_offset == 999

    # Doc truncation.
    doc = TextDoc.from_text(_example_text)
    truncated_doc = truncate_at_wordtok_offset(doc, 10)
    expected_text = "This is the first paragraph."
    expected_doc = TextDoc.from_text(expected_text)
    assert truncated_doc.reassemble() == expected_doc.reassemble()

    truncated_doc = truncate_at_wordtok_offset(doc, 34)
    expected_text = "This is the first paragraph. It has multiple sentences.\n\nThis is the second paragraph. It also"
    print(truncated_doc.reassemble())
    expected_doc = TextDoc.from_text(expected_text)
    assert truncated_doc.reassemble() == expected_doc.reassemble()