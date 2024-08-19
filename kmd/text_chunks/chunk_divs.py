from textwrap import dedent
from typing import List
from kmd.model.errors_model import InvalidInput
from kmd.model.html_conventions import CHUNK, ORIGINAL
from kmd.text_chunks.para_groups import para_groups_by_size
from kmd.text_chunks.parse_divs import TextNode, parse_divs
from kmd.text_docs.text_doc import TextDoc, TextUnit
from kmd.text_formatting.html_in_md import div_wrapper


chunk_wrapper = div_wrapper(class_name=CHUNK, padding="\n\n")

original_wrapper = div_wrapper(class_name=ORIGINAL, padding="\n\n")


def chunk_paras_into_divs(text: str, min_size: int, unit: TextUnit) -> str:
    """
    Add HTML "chunk" divs around paragraphs, where each chunk is at least the
    specified minimum size.
    """
    doc = TextDoc.from_text(text)

    chunks = para_groups_by_size(doc, min_size, unit)
    return "\n\n".join(chunk_wrapper(chunk.reassemble()) for chunk in chunks)


def parse_chunk_divs(text: str) -> List[TextNode]:
    """
    Parse div chunks into TextNodes.
    """

    text_node = parse_divs(text)

    chunk_divs = text_node.children_with_class_names(CHUNK)

    if not chunk_divs:
        raise InvalidInput("No chunk divs found in text.")

    return chunk_divs


## Tests


_med_test_doc = dedent(
    """
        # Title

        Hello World. This is an example sentence. And here's another one!

        ## Subtitle

        This is a new paragraph.
        It has several sentences.
        There may be line breaks within a paragraph, but these should not affect handlingof the paragraph.
        There are also [links](http://www.google.com) and **bold** and *italic* text.

        ### Itemized List

        - Item 1

        - Item 2

        - Item 3

        <div>  extra 
        </div>

        Blah blah.
        """
).strip()


def test_chunk_paras_as_divs():
    assert chunk_paras_into_divs("", 7, TextUnit.words) == ""
    assert (
        chunk_paras_into_divs("hello", 100, TextUnit.words)
        == '<div class="chunk">\n\nhello\n\n</div>'
    )

    chunked = chunk_paras_into_divs(_med_test_doc, 7, TextUnit.words)

    print("Chunked doc:\n---\n" + chunked + "\n---")

    expected_first_chunk = dedent(
        """
        <div class="chunk">

        # Title

        Hello World. This is an example sentence. And here's another one!

        </div>
        """
    ).strip()

    assert chunked.startswith(expected_first_chunk)
    assert chunked.endswith("</div>")
    assert chunked.count("<div class=") == 4
    assert chunked.count("</div>") == 5  # Extra spurious </div>.


def test_parse_chunk_divs():
    text = dedent(
        """
        <div class="chunk">

        Chunk 1 text.

        </div>

        <div class="chunk">

        Chunk 2 text.

        </div>

        <div class="chunk">Empty chunk.</div>

        """
    )

    chunk_divs = parse_chunk_divs(text)

    print("\n---")
    for chunk_div in chunk_divs:
        print(chunk_div.reassemble())
        print("---")

    assert chunk_divs[0].reassemble() == """<div class="chunk">\nChunk 1 text.\n</div>"""
    assert chunk_divs[0].content.strip() == "Chunk 1 text."
    assert len(chunk_divs) == 3
