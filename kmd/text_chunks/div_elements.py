from textwrap import dedent
from kmd.config.logger import get_logger
from kmd.model.doc_elements import CHUNK, ORIGINAL
from kmd.text_chunks.chunk_utils import chunk_children, chunk_paras
from kmd.text_chunks.parse_divs import TextNode, parse_divs
from kmd.text_docs.text_doc import TextDoc, TextUnit
from kmd.text_docs.wordtoks import first_wordtok_is_div
from kmd.text_formatting.html_in_md import div_wrapper, html_join_blocks

log = get_logger(__name__)


def div(class_name: str, *blocks: str) -> str:
    """
    Convenience to create Markdown-compatible div with HTML in its own paragraphs.
    """
    return div_wrapper(class_name=class_name, padding="\n\n")(html_join_blocks(*blocks))


def div_wrap_if_needed(element: TextNode, class_name: str) -> str:
    """
    Wrap the chunk contents in an "original" div if it's not already there.
    """
    has_original_div = bool(element.child_by_class_name(class_name))
    if has_original_div:
        return element.contents
    else:
        return div(class_name, element.contents.strip())


def div_get_child_if_present(element: TextNode, class_name: str) -> str:
    """
    Use named child element if it exists, otherwise use the whole contents.
    """
    child = element.child_by_class_name(class_name)
    return child.contents if child else element.contents


def div_insert_sibling(
    element: TextNode,
    new_child_str: str,
    container_class: str,
    sibling_class: str,
    insert_before: bool = True,
) -> str:
    """
    Insert a new child into a chunk div. Wrap the previous chunk contents in an "original" div
    if it's not already there.
    """

    if element.class_name != container_class:
        raise ValueError(f"Expected a container div '{element}' but got: {element}")

    chunk_str = div_wrap_if_needed(element, sibling_class)

    if insert_before:
        blocks = [new_child_str, chunk_str]
    else:
        blocks = [chunk_str, new_child_str]

    return div(container_class, html_join_blocks(*blocks))


def chunk_text_as_divs(text: str, min_size: int, unit: TextUnit, class_name: str = CHUNK) -> str:
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


## Tests


def test_div_insert_child():
    chunk = parse_divs(div(CHUNK, "Chunk text.")).children[0]

    new_child_str = div("new", "New child text.")

    new_chunk_str = div_insert_sibling(
        chunk, new_child_str, container_class=CHUNK, sibling_class=ORIGINAL
    )

    print("\n---test_div_insert_child---")
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


def test_chunk_text_into_divs():
    assert chunk_text_as_divs("", 7, TextUnit.words) == ""
    assert (
        chunk_text_as_divs("hello", 100, TextUnit.words) == '<div class="chunk">\n\nhello\n\n</div>'
    )

    chunked = chunk_text_as_divs(_med_test_doc, 7, TextUnit.words)

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
