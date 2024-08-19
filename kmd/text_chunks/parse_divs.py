import re
from textwrap import dedent
import copy

from kmd.text_chunks.text_node import TextNode


DIV_TAGS = re.compile(r"(<div\b[^>]*>|</div>)", re.IGNORECASE)

CLASS_NAME_PATTERN = re.compile(r"\bclass=\"([^\"]+)\"", re.IGNORECASE)


def parse_divs(text: str, skip_whitespace: bool = True) -> TextNode:
    """
    Parse a string recursively into TextNodes based on `<div>` tags.

    All offsets are relative to the original text. Text outside of a div is included
    as a TextNode with None markers.

    We do our own parsing to keep this simple and exactly preserve formatting.
    """
    parsed = _parse_divs_recursive(
        text, 0, TextNode(original_text=text, offset=0, content_start=0, content_end=len(text))
    )

    if skip_whitespace:
        parsed = _skip_whitespace_nodes(parsed)

    return parsed


def _skip_whitespace_nodes(node: TextNode) -> TextNode:
    filtered_node = copy.copy(node)
    filtered_node.children = [
        _skip_whitespace_nodes(child) for child in node.children if not child.is_whitespace()
    ]
    return filtered_node


def _parse_divs_recursive(
    text: str,
    start_offset: int,
    result: TextNode,
) -> TextNode:
    current_offset = start_offset

    while current_offset < len(text):
        match = DIV_TAGS.search(text, current_offset)

        if not match:
            # No more div tags, add remaining content as a child node
            if current_offset < len(text):
                result.children.append(
                    TextNode(
                        original_text=text,
                        offset=current_offset,
                        content_start=current_offset,
                        content_end=len(text),
                    )
                )
            break

        if match.start() > current_offset:
            # Add content before the div tag as a child node.
            result.children.append(
                TextNode(
                    original_text=text,
                    offset=current_offset,
                    content_start=current_offset,
                    content_end=match.start(),
                )
            )

        tag = match.group(1)
        is_end_tag = tag.startswith("</")

        if is_end_tag:
            # Closing tag. We're done with this node.
            result.end_marker = tag
            result.content_end = match.start()
            current_offset = match.end()
            break
        else:
            # Opening tag. Create a new child node and recurse.
            class_match = CLASS_NAME_PATTERN.search(tag)
            class_name = class_match.group(1) if class_match else None

            child_node = TextNode(
                original_text=text,
                offset=match.start(),
                content_start=match.end(),
                content_end=len(text),
                tag_name="div",
                class_name=class_name,
                begin_marker=tag,
            )

            child_node = _parse_divs_recursive(text, match.end(), child_node)

            result.children.append(child_node)

            current_offset = child_node.end_offset

    return result


## Tests


def test_parse_divs():
    text = dedent(
        """

        <div class="outer">
            Outer content paragraph 1.

            Outer content paragraph 2.
            <div class="inner">
                Inner content.
                <div>
                    Nested content.
                </div>

                <div class="nested-inner">

                    Nested inner content.
                    <div>
                        Deeply nested content.
                    </div>
                </div>

                
            </div>
            Outer content paragraph 3.
        </div>
        """
    )

    def validate_node(node: TextNode, original_text: str):
        assert node.original_text == original_text
        assert 0 <= node.content_start <= len(original_text)
        assert 0 <= node.content_end <= len(original_text)
        assert node.content_start <= node.content_end
        assert node.contents == original_text[node.content_start : node.content_end]
        assert (
            node.begin_marker is None
            or original_text[node.offset : node.offset + len(node.begin_marker)]
            == node.begin_marker
        )
        assert (
            node.end_marker is None
            or original_text[node.content_end : node.content_end + len(node.end_marker)]
            == node.end_marker
        )

        for child in node.children:
            validate_node(child, original_text)

    node = parse_divs(text, skip_whitespace=False)

    node_no_whitespace = parse_divs(text, skip_whitespace=True)

    reassembled = node.reassemble(padding="")

    print()
    print(f"Original text (length {len(text)}):")
    print(text)

    print()
    print("Parsed text:")
    print(node)

    print()
    print("Parsed text (no whitespace):")
    print(node_no_whitespace)

    print()
    print(f"Reassembled text (length {len(reassembled)}):")
    print(reassembled)

    print()
    print("Reassembled text (normalized padding):")
    print(node.reassemble())

    validate_node(node, text)

    assert reassembled.count("<div") == reassembled.count("</div")

    assert node.reassemble(padding="") == text
