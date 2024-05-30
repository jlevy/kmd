"""
Transform text using sliding windows over a document, then reassembling the
transformed text.
"""

from dataclasses import dataclass
from math import ceil
from textwrap import dedent
from typing import Callable, Generator, List, Optional
from pprint import pprint
from kmd.config.logger import get_logger
from kmd.text_handling.text_diffs import find_best_alignment
from kmd.text_handling.text_doc import (
    DocIndex,
    Paragraph,
    Sentence,
    TextDoc,
    Unit,
    size,
    size_in_bytes,
)
from kmd.text_handling.wordtoks import (
    PARA_BR_STR,
    SENT_BR_STR,
    join_wordtoks,
    sentence_as_wordtoks,
)


log = get_logger(__name__)


def seek_doc(doc: TextDoc, offset: int, unit: Unit) -> DocIndex:
    """
    Find the last sentence that starts before a given offset.
    """
    current_size = 0
    last_fit_index = None

    if unit == Unit.BYTES:
        size_sent_break = size_in_bytes(SENT_BR_STR)
        size_para_break = size_in_bytes(PARA_BR_STR)
    elif unit == Unit.CHARS:
        size_sent_break = len(SENT_BR_STR)
        size_para_break = len(PARA_BR_STR)
    elif unit == Unit.WORDTOKS:
        size_sent_break = 1
        size_para_break = 1
    else:
        raise ValueError(f"Unsupported unit for seek_doc: {unit}")

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

    if last_fit_index is None:
        raise ValueError("Cannot seek into empty document")

    return last_fit_index


def _truncate_sent_at_wordtok_offset(sent: Sentence, offset: int) -> Sentence:
    """
    Truncate a sentence to the given number of wordtoks.
    """
    wordtoks = sentence_as_wordtoks(sent.text)
    truncated_wordtoks = wordtoks[:offset]
    joined = join_wordtoks(truncated_wordtoks)
    return Sentence(joined, sent.char_offset)


def truncate_at_wordtok_offset(doc: TextDoc, offset: int) -> TextDoc:
    """
    Truncate a document at a given wordtok offset.
    """
    index = seek_doc(doc, offset, Unit.WORDTOKS)
    try:
        sub_doc = doc.sub_doc(DocIndex(0, 0), doc.prev_sent(index))
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

        start_offset += window_shift
        start_index = end_index


def sliding_para_window(doc: TextDoc, nparas: int) -> Generator[TextDoc, None, None]:
    """
    Generate TextDoc sub-documents taking `nparas` paragraphs at a time.
    """
    for i in range(0, len(doc.paragraphs), nparas):
        end_index = min(i + nparas - 1, len(doc.paragraphs) - 1)
        yield doc.sub_doc(DocIndex(i, 0), DocIndex(end_index, 0))


TextDocTransform = Callable[[TextDoc], TextDoc]

WINDOW_BR = "<!--window-br-->"


@dataclass
class WindowSettings:
    """
    Size of the sliding window, the shift, and the min overlap required when stitching windows
    together. All sizes in wordtoks.
    """

    unit: Unit
    size: int
    shift: int
    min_overlap: int = 0
    separator: str = ""


# Sliding, overlapping word-based window. 2K wordtoks is several paragraphs.
WINDOW_2K_WORDTOKS = WindowSettings(Unit.WORDTOKS, 2048, 2048 - 256, 8, separator=WINDOW_BR)

# Process 4 paragraphs at a time.
WINDOW_4_PARAS = WindowSettings(Unit.PARAGRAPHS, 4, 4, 0, separator=WINDOW_BR)


def sliding_window_transform(
    doc: TextDoc,
    transform_func: TextDocTransform,
    settings: WindowSettings,
) -> TextDoc:
    if settings.unit == Unit.WORDTOKS:
        return sliding_word_window_transform(doc, transform_func, settings)
    elif settings.unit == Unit.PARAGRAPHS:
        return sliding_para_window_transform(doc, transform_func, settings)
    else:
        raise ValueError(f"Unsupported sliding transform unit: {settings.unit}")


def sliding_word_window_transform(
    doc: TextDoc,
    transform_func: TextDocTransform,
    settings: WindowSettings,
) -> TextDoc:
    """
    Apply a transformation function to each TextDoc in a sliding window over the given document,
    stepping through wordtoks, then reassemble the transformed document. Uses best effort to
    stitch the results together seamlessly by searching for the best alignment (minimum wordtok
    edit distance) of each transformed window.
    """
    if settings.unit != Unit.WORDTOKS:
        raise ValueError(f"This sliding window expects wordtoks, not {settings.unit}")

    output_wordtoks = []
    windows = sliding_word_window(doc, settings.size, settings.shift, Unit.WORDTOKS)
    nwordtoks = doc.size(Unit.WORDTOKS)
    nbytes = doc.size(Unit.BYTES)
    nwindows = (nwordtoks - settings.size) // settings.shift + 1
    sep_wordtoks = [settings.separator] if settings.separator else []

    log.message(
        "Sliding word transform: Begin on doc: total %s wordtoks, %s bytes, %s windows, %s",
        nwordtoks,
        nbytes,
        nwindows,
        settings,
    )

    for i, window in enumerate(windows):
        log.message(
            "Sliding word transform: Window %s (%s wordtoks, %s bytes), at %s wordtoks so far",
            i,
            window.size(Unit.WORDTOKS),
            window.size(Unit.BYTES),
            len(output_wordtoks),
        )
        transformed_window = transform_func(window)
        new_wordtoks = list(transformed_window.as_wordtoks())
        if not output_wordtoks:
            output_wordtoks = new_wordtoks
        else:
            offset, (score, diff) = find_best_alignment(
                output_wordtoks, new_wordtoks, settings.min_overlap
            )
            log.message(
                "Sliding word transform: Best alignment of window %s is at token offset %s (score %s, %s)",
                i,
                offset,
                score,
                diff.stats(),
            )

            output_wordtoks = output_wordtoks[:offset] + sep_wordtoks + new_wordtoks

    log.message("Sliding word transform: Done, output total %s wordtoks", len(output_wordtoks))

    # An alternate approach would be to accumulate the document sentences instead of wordtoks to
    # avoid re-parsing, but this probably a little simpler.
    output_doc = TextDoc.from_text(join_wordtoks(output_wordtoks))
    return output_doc


def sliding_para_window_transform(
    doc: TextDoc, transform_func: TextDocTransform, settings: WindowSettings
) -> TextDoc:
    """
    Apply a transformation function to each TextDoc, stepping through paragraphs `settings.size`
    at a time, then reassemble the transformed document.
    """
    if settings.unit != Unit.PARAGRAPHS:
        raise ValueError(f"This sliding window expects paragraphs, not {settings.unit}")
    if settings.size != settings.shift:
        raise ValueError("Paragraph window transform requires equal size and shift")

    windows = sliding_para_window(doc, settings.size)

    log.message(
        "Sliding paragraph transform: Begin on doc: %s windows of size %s paragraphs on total %s",
        ceil(doc.size(Unit.PARAGRAPHS) / settings.size),
        settings.size,
        doc.size_summary(),
    )

    transformed_paras: List[Paragraph] = []
    for i, window in enumerate(windows):
        log.message(
            "Sliding paragraph transform: Begin on doc: window %s",
            window.size_summary(),
        )

        new_doc = transform_func(window)
        if i > 0:
            try:
                new_doc.paragraphs[0].sentences[0].text = (
                    settings.separator + new_doc.paragraphs[0].sentences[0].text
                )
            except KeyError:
                pass
        transformed_paras.extend(new_doc.paragraphs)

    transformed_text = f"\n\n".join(para.reassemble() for para in transformed_paras)
    new_text_doc = TextDoc.from_text(transformed_text)

    log.message(
        "Sliding paragraph transform: Done, output total %s",
        new_text_doc.size_summary(),
    )

    return new_text_doc


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


def test_sliding_word_window_transform():
    long_text = (_example_text + "\n\n") * 2
    doc = TextDoc.from_text(long_text)

    # Simple transformation that converts all text to uppercase.
    def transform_func(window: TextDoc) -> TextDoc:
        transformed_text = window.reassemble().upper()
        return TextDoc.from_text(transformed_text)

    transformed_doc = sliding_window_transform(
        doc, transform_func, WindowSettings(Unit.WORDTOKS, 80, 60, min_overlap=5, separator="|")
    )
    print("---Wordtok transformed doc:")
    print(transformed_doc.reassemble())

    assert transformed_doc.reassemble().count("|") == 2

    long_text = (_example_text + "\n\n") * 20
    doc = TextDoc.from_text(long_text)
    transformed_doc = sliding_window_transform(
        doc, transform_func, WindowSettings(Unit.WORDTOKS, 80, 60, min_overlap=5)
    )
    assert transformed_doc.reassemble() == long_text.upper().strip()


def test_sliding_para_window_transform():
    def transform_func(window: TextDoc) -> TextDoc:
        transformed_text = window.reassemble().upper()
        return TextDoc.from_text(transformed_text)

    text = "\n\n".join(f"Paragraph {i}." for i in range(7))
    doc = TextDoc.from_text(text)

    transformed_doc = sliding_para_window_transform(
        doc,
        transform_func,
        WindowSettings(
            Unit.PARAGRAPHS,
            3,
            3,
            separator=WINDOW_BR,
        ),
    )

    print("---Paragraph transformed doc:")
    print(transformed_doc.reassemble())

    assert (
        transformed_doc.reassemble()
        == dedent(
            """
            PARAGRAPH 0.

            PARAGRAPH 1.

            PARAGRAPH 2.

            <!--window-br-->PARAGRAPH 3.

            PARAGRAPH 4.

            PARAGRAPH 5.

            <!--window-br-->PARAGRAPH 6.
            """
        ).strip()
    )
