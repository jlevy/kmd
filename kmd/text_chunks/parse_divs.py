from dataclasses import dataclass
import re
from typing import Generator, Optional
from kmd.util.obj_utils import abbreviate_obj


@dataclass(frozen=True)
class Chunk:
    original_text: str
    offset: int
    content_start: int
    content_end: int
    class_name: str
    begin_marker: Optional[str] = None
    end_marker: Optional[str] = None

    def content(self) -> str:
        return self.original_text[self.content_start : self.content_end]

    def __str__(self):
        return abbreviate_obj(self)


def div_begin_tag(class_name: str) -> str:
    return f'<div class="{class_name}">'


def div_end_tag() -> str:
    return "</div>"


div_pattern = re.compile(r"(<div\b[^>]*>|</div>)")


def parse_chunk_divs(text: str, class_name: str) -> Generator[Chunk, None, None]:
    """
    Parse a string and yield non-empty Chunks of paragraphs based on
    `<div class="...">`/`</div>` blocks.

    Text outside chunk divs is returned in Chunks with None markers.
    Handles nested divs correctly and skips empty (whitespace-only) chunks.
    """
    current_pos = 0
    text_length = len(text)

    div_begin = div_begin_tag(class_name)
    div_end = div_end_tag()

    while current_pos < text_length:
        chunk_start = text.find(div_begin, current_pos)

        if chunk_start == -1:
            # No more chunk divs, yield remaining non-empty text as a Chunk with None markers.
            remaining_text = text[current_pos:].strip()
            if remaining_text:
                yield Chunk(
                    original_text=text,
                    offset=current_pos,
                    content_start=current_pos,
                    content_end=text_length,
                    class_name=class_name,
                )
            break

        if chunk_start > current_pos:
            # Yield non-empty text before the chunk div as a Chunk with None markers.
            pre_chunk_text = text[current_pos:chunk_start].strip()
            if pre_chunk_text:
                yield Chunk(
                    original_text=text,
                    offset=current_pos,
                    content_start=current_pos,
                    content_end=chunk_start,
                    class_name=class_name,
                )

        # Find the matching end div.
        nesting_level = 1
        chunk_end = chunk_start + len(div_begin)
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
        content_start = chunk_start + len(div_begin)
        content_end = chunk_end - len(div_end)
        chunk_content = text[content_start:content_end].strip()
        if chunk_content:
            yield Chunk(
                original_text=text,
                offset=chunk_start,
                content_start=content_start,
                content_end=content_end,
                class_name=class_name,
                begin_marker=div_begin,
                end_marker=div_end,
            )

        current_pos = chunk_end

    if current_pos < text_length:
        # Yield any remaining non-empty text as a Chunk with None markers.
        remaining_text = text[current_pos:].strip()
        if remaining_text:
            yield Chunk(
                original_text=text,
                offset=current_pos,
                content_start=current_pos,
                content_end=text_length,
                class_name=class_name,
                begin_marker=None,
                end_marker=None,
            )
