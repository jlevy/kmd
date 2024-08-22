from textwrap import dedent
from kmd.config.logger import get_logger
from kmd.model.html_conventions import CHUNK, ORIGINAL
from kmd.text_chunks.chunk_utils import chunk_children, chunk_paras
from kmd.text_chunks.parse_divs import TextNode, parse_divs
from kmd.text_docs.text_doc import TextDoc, TextUnit
from kmd.text_docs.wordtoks import first_wordtok_is_div
from kmd.text_formatting.html_in_md import div_wrapper, html_div, html_join_blocks

log = get_logger(__name__)

div_chunk = div_wrapper(class_name=CHUNK, padding="\n\n")


def div(class_name: str, *blocks: str) -> str:
    return div_wrapper(class_name=class_name, padding="\n\n")(html_join_blocks(*blocks))


def chunk_text_into_divs(text: str, min_size: int, unit: TextUnit, class_name: str = CHUNK) -> str:
    """
    Add HTML divs around "chunks" of text paragraphs or top-level divs, where each chunk is at least the
    specified minimum size.
    """

    if first_wordtok_is_div(text):
        log.message("Chunking paragraphs using divs.")
        parsed = parse_divs(text)
        chunks = chunk_children(parsed, min_size, unit)
        chunk_strs = [chunk.reassemble() for chunk in chunks]
        size_summary = parsed.size_summary()
    else:
        log.message("Chunking paragraphs using newlines.")
        doc = TextDoc.from_text(text)
        chunks = chunk_paras(doc, min_size, unit)
        chunk_strs = [chunk.reassemble() for chunk in chunks]
        size_summary = doc.size_summary()

    div_chunks = [div(class_name, chunk_str) for chunk_str in chunk_strs]

    log.message("Added %s div chunks on doc:\n%s", len(div_chunks), size_summary)

    return "\n\n".join(div_chunks)


def add_original(chunk: TextNode) -> str:
    """
    Wrap the chunk contents in an "original" div if it's not already there.
    """
    has_original_div = bool(chunk.child_by_class_name(ORIGINAL))
    if has_original_div:
        return chunk.contents
    else:
        return div(ORIGINAL, chunk.contents.strip())


def get_original(chunk: TextNode) -> str:
    """
    Use "original" div contents if it exists, otherwise use the whole contents.
    """
    original = chunk.child_by_class_name(ORIGINAL)
    return original.contents if original else chunk.contents


def insert_chunk_child(
    chunk: TextNode, new_child_str: str, insert_before: bool = True, class_name: str = CHUNK
) -> str:
    """
    Insert a new child into a chunk div. Wrap the chunk contents in an "original" div
    if it's not already there.
    """

    if chunk.class_name != class_name:
        raise ValueError(f"Expected a div chunk: {chunk}")

    chunk_str = add_original(chunk)

    if insert_before:
        blocks = [new_child_str, chunk_str]
    else:
        blocks = [chunk_str, new_child_str]

    return div(class_name, html_join_blocks(*blocks))


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
    assert chunk_text_into_divs("", 7, TextUnit.words) == ""
    assert (
        chunk_text_into_divs("hello", 100, TextUnit.words)
        == '<div class="chunk">\n\nhello\n\n</div>'
    )

    chunked = chunk_text_into_divs(_med_test_doc, 7, TextUnit.words)

    print("\n---test_chunk_paras_as_divs---")
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


def test_insert_chunk_child():
    chunk = parse_divs(div_chunk("Chunk text.")).children[0]

    new_child_str = html_div("New child text.", class_name="new", padding="\n\n")

    new_chunk_str = insert_chunk_child(chunk, new_child_str)

    print("\n---test_insert_chunk_child---")
    print("\nInserting into chunk:")
    print(chunk.original_text)
    print("\nNew child:")
    print(new_child_str)
    print("\nNew chunk:")
    print(new_chunk_str)

    assert (
        new_chunk_str
        == dedent(
            """
            <div class="chunk">

            <div class="new">

            New child text.

            </div>

            <div class="original">

            Chunk text.

            </div>

            </div>
            """
        ).strip()
    )
