from dataclasses import dataclass
import re
from textwrap import dedent
from typing import Generator, Optional
from kmd.model.html_conventions import CHUNK, CHUNK_DIV_BEGIN, DIV_END
from kmd.text_docs.para_groups import para_groups_by_size
from kmd.text_docs.text_doc import TextDoc, TextUnit
from kmd.text_formatting.html_in_md import div_wrapper


chunk_wrapper = div_wrapper(class_name=CHUNK, padding="\n\n")


def chunk_paras_into_divs(text: str, min_size: int, unit: TextUnit) -> str:
    """
    Add HTML "chunk" divs around paragraphs, where each chunk is at least the
    specified minimum size.
    """
    doc = TextDoc.from_text(text)

    chunks = para_groups_by_size(doc, min_size, unit)
    return "\n\n".join(chunk_wrapper(chunk.reassemble()) for chunk in chunks)


@dataclass
class Chunk:
    content: str
    offset: int
    begin_marker: Optional[str] = None
    end_marker: Optional[str] = None


def parse_chunk_divs(text: str) -> Generator[Chunk, None, None]:
    """
    Parse a string and yield non-empty Chunks based on `<div class="chunk">`/`</div>` blocks.

    Text outside chunk divs is returned in Chunks with None markers.
    Handles nested divs correctly and skips empty chunks.
    """
    current_pos = 0
    text_length = len(text)
    div_pattern = re.compile(r"(<div\b[^>]*>|</div>)")

    while current_pos < text_length:
        chunk_start = text.find(CHUNK_DIV_BEGIN, current_pos)

        if chunk_start == -1:
            # No more chunk divs, yield remaining non-empty text as a Chunk with None markers.
            remaining_text = text[current_pos:].strip()
            if remaining_text:
                yield Chunk(remaining_text, current_pos, None, None)
            break

        if chunk_start > current_pos:
            # Yield non-empty text before the chunk div as a Chunk with None markers.
            pre_chunk_text = text[current_pos:chunk_start].strip()
            if pre_chunk_text:
                yield Chunk(pre_chunk_text, current_pos, None, None)

        # Find the matching end div.
        nesting_level = 1
        chunk_end = chunk_start + len(CHUNK_DIV_BEGIN)
        while nesting_level > 0 and chunk_end < text_length:
            match = div_pattern.search(text, chunk_end)
            if not match:
                break

            if match.group(1).startswith("</div"):
                nesting_level -= 1
            else:
                nesting_level += 1

            chunk_end = match.end()

        if nesting_level > 0:
            # Unclosed chunk div, treat the rest as part of the chunk.
            chunk_end = text_length

        # Yield chunk content with begin and end markers.
        content_start = chunk_start + len(CHUNK_DIV_BEGIN)
        content_end = chunk_end - len(DIV_END)
        chunk_content = text[content_start:content_end].strip()
        if chunk_content:
            yield Chunk(chunk_content, chunk_start, CHUNK_DIV_BEGIN, DIV_END)

        current_pos = chunk_end

    if current_pos < text_length:
        # Yield any remaining non-empty text as a Chunk with None markers.
        remaining_text = text[current_pos:].strip()
        if remaining_text:
            yield Chunk(remaining_text, current_pos, None, None)


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

    print(chunked)

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

    parsed = list(parse_chunk_divs(chunked))

    print("\n\n".join(str(chunk) for chunk in parsed))

    assert parsed[0] == Chunk(
        content="# Title\n\nHello World. This is an example sentence. And here's another one!",
        offset=0,
        begin_marker='<div class="chunk">',
        end_marker="</div>",
    )
    assert len(parsed) == 4
