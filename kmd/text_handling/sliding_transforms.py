"""
Transform text using sliding windows over a document, then reassembling the
transformed text.
"""

from dataclasses import dataclass
from math import ceil
from textwrap import dedent
from typing import Callable, List, Optional
from kmd.config.logger import get_logger
from kmd.config.text_styles import EMOJI_PROCESS, EMOJI_WARN
from kmd.model.errors_model import UnexpectedError
from kmd.model.items_model import Format
from kmd.text_handling.markdown_normalization import normalize_markdown
from kmd.text_handling.sliding_windows import sliding_para_window, sliding_word_window
from kmd.text_handling.text_diffs import ALL_CHANGES, DiffOpFilter, diff_docs, find_best_alignment
from kmd.text_handling.text_doc import (
    Paragraph,
    TextDoc,
    Unit,
)
from kmd.text_handling.text_formatting import format_lines
from kmd.text_handling.wordtoks import (
    join_wordtoks,
)

log = get_logger(__name__)

TextDocTransform = Callable[[TextDoc], TextDoc]

WINDOW_BR = "\n<!--window-br-->\n"


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

    def __str__(self):
        return f"windowing size={self.size}, shift={self.shift}, min_overlap={self.min_overlap} {self.unit.value}"


def filtered_transform(
    doc: TextDoc,
    transform_func: TextDocTransform,
    windowing: Optional[WindowSettings],
    diff_filter: DiffOpFilter = ALL_CHANGES,
) -> TextDoc:
    """
    Apply a transform with sliding window across the input doc, enforcing
    the changes it's allowed to make with `diff_filter`.
    """

    if not windowing:
        transformed_doc = transform_func(doc)
    else:

        def transform_and_check_diff(input_doc: TextDoc) -> TextDoc:
            result_doc = transform_func(input_doc)

            # Check the transform did what it should have.
            diff = diff_docs(input_doc, result_doc)
            accepted_diff, rejected_diff = diff.filter(diff_filter)

            assert diff.left_size() == input_doc.size(Unit.WORDTOKS)
            assert accepted_diff.left_size() == input_doc.size(Unit.WORDTOKS)
            assert rejected_diff.left_size() == input_doc.size(Unit.WORDTOKS)

            log.info(
                "Accepted changes: %s:\n%s",
                accepted_diff.stats(),
                format_lines(str(accepted_diff).splitlines()),
            )

            # Note any rejections.
            rejected_changes = rejected_diff.changes()
            if rejected_changes:
                log.warning(
                    "%s Rejected changes: %s:\n%s",
                    EMOJI_WARN,
                    rejected_diff.stats(),
                    format_lines(str(rejected_diff).splitlines()),
                )

            # Apply only the accepted changes.
            final_doc = TextDoc.from_wordtoks(accepted_diff.apply_to(input_doc.as_wordtoks()))

            log.message(
                "Word token changes:\n%s",
                format_lines(
                    [f"Accepted: {accepted_diff.stats()}", f"Rejected: {rejected_diff.stats()}"]
                ),
            )

            log.save_object(
                "Input doc normalized",
                "transform_and_check_diff",
                normalize_markdown(input_doc.reassemble()),
            )
            log.save_object(
                "Result doc normalized",
                "transform_and_check_diff",
                normalize_markdown(result_doc.reassemble()),
            )
            log.save_object("Transform diff", "transform_and_check_diff", diff)
            log.save_object("Accepted diff", "transform_and_check_diff", accepted_diff)
            log.save_object("Rejected diff", "transform_and_check_diff", rejected_diff)
            log.save_object("Final doc", "transform_and_check_diff", final_doc.reassemble())

            return final_doc

        transformed_doc = sliding_window_transform(
            doc,
            transform_and_check_diff,
            windowing,
        )

    return transformed_doc


def sliding_window_transform(
    doc: TextDoc,
    transform_func: TextDocTransform,
    settings: WindowSettings,
) -> TextDoc:
    if settings.unit == Unit.WORDTOKS:
        return sliding_wordtok_window_transform(doc, transform_func, settings)
    elif settings.unit == Unit.PARAGRAPHS:
        return sliding_para_window_transform(doc, transform_func, settings)
    else:
        raise UnexpectedError(f"Unsupported sliding transform unit: {settings.unit}")


def sliding_wordtok_window_transform(
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

    windows = sliding_word_window(doc, settings.size, settings.shift, Unit.WORDTOKS)

    nwordtoks = doc.size(Unit.WORDTOKS)
    nbytes = doc.size(Unit.BYTES)
    nwindows = ceil(nwordtoks / settings.size)
    sep_wordtoks = [settings.separator] if settings.separator else []

    log.message(
        "%s Sliding word transform: Begin on doc: total %s wordtoks, %s bytes, %s windows, %s",
        EMOJI_PROCESS,
        nwordtoks,
        nbytes,
        nwindows,
        settings,
    )

    output_wordtoks = []
    for i, window in enumerate(windows):
        log.message(
            "%s Sliding word transform: Window %s of %s (%s wordtoks, %s bytes), at %s wordtoks so far",
            EMOJI_PROCESS,
            i,
            nwindows,
            window.size(Unit.WORDTOKS),
            window.size(Unit.BYTES),
            len(output_wordtoks),
        )

        transformed_window = transform_func(window)

        new_wordtoks = transformed_window.as_wordtoks()

        if not output_wordtoks:
            output_wordtoks = new_wordtoks
        else:
            offset, (score, diff) = find_best_alignment(
                output_wordtoks, new_wordtoks, settings.min_overlap
            )

            log.message(
                "%s Sliding word transform: Best alignment of window %s is at token offset %s (score %s, %s)",
                EMOJI_PROCESS,
                i,
                offset,
                score,
                diff.stats(),
            )

            output_wordtoks = output_wordtoks[:offset] + sep_wordtoks + new_wordtoks

    log.message(
        "%s Sliding word transform: Done, output total %s wordtoks",
        EMOJI_PROCESS,
        len(output_wordtoks),
    )

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

    windows = sliding_para_window(doc, settings.size, format=Format.markdown)

    nwindows = ceil(doc.size(Unit.PARAGRAPHS) / settings.size)
    log.message(
        "Sliding paragraph transform: Begin on doc: %s windows of size %s paragraphs on total %s",
        nwindows,
        settings.size,
        doc.size_summary(),
    )

    transformed_paras: List[Paragraph] = []
    for i, window in enumerate(windows):
        log.message(
            "Sliding paragraph transform: Window %s/%s input is %s",
            i,
            nwindows,
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

            <!--window-br-->
            PARAGRAPH 3.

            PARAGRAPH 4.

            PARAGRAPH 5.

            <!--window-br-->
            PARAGRAPH 6.
            """
        ).strip()
    )
