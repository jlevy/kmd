from textwrap import dedent
from typing import Callable, Generator
from kmd.model.html_conventions import CHUNK
from kmd.text_docs.text_doc import TextDoc, TextUnit
from kmd.text_formatting.html_in_md import div_wrapper


def para_groups(
    doc: TextDoc, condition: Callable[[TextDoc], bool]
) -> Generator[TextDoc, None, None]:
    """
    Walk through the paragraphs of a TextDoc and yield sequential subdocs
    once they meet a specific condition.
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


def para_groups_as_divs(doc: TextDoc, min_size: int, unit: TextUnit) -> Generator[str, None, None]:
    """
    Generate HTML div strings with class "chunk" from a TextDoc,
    where each chunk is at least the specified minimum size.
    """
    condition = lambda subdoc: subdoc.size(unit) >= min_size
    chunk_wrapper = div_wrapper(class_name=CHUNK, padding="\n\n")

    for chunk in para_groups(doc, condition):
        yield chunk_wrapper(chunk.reassemble())


def chunk_paras_into_divs(text: str, min_size: int, unit: TextUnit) -> str:
    """
    Add HTML "chunk" divs, where each chunk is at least the specified minimum size.
    """
    doc = TextDoc.from_text(text)
    return "\n\n".join(para_groups_as_divs(doc, min_size, unit))


## Tests


def test_chunk_paras_as_divs():

    assert chunk_paras_into_divs("", 7, TextUnit.WORDS) == ""
    assert (
        chunk_paras_into_divs("hello", 100, TextUnit.WORDS)
        == '<div class="chunk">\n\nhello\n\n</div>'
    )

    from kmd.text_docs.text_doc import _med_test_doc

    chunked = chunk_paras_into_divs(_med_test_doc, 7, TextUnit.WORDS)

    expected_first_chunk = dedent(
        """
        <div class="chunk">

        # Title

        Hello World. This is an example sentence. And here's another one!

        </div>
        """
    ).strip()

    assert (
        chunked.startswith(expected_first_chunk)
        and chunked.endswith("</div>")
        and chunked.count("<div class=") == 5
        and chunked.count("</div>") == 5
    )
