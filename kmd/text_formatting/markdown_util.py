from typing import List
import marko
from marko.inline import Link
from marko.block import ListItem, Heading
from kmd.config.logger import get_logger

log = get_logger(__name__)


def markdown_to_html(markdown: str) -> str:
    """
    Convert Markdown to HTML.
    """
    return marko.convert(markdown)


def _tree_links(element, include_internal=False):
    links = []

    def _find_links(element):
        match element:
            case Link():
                if include_internal or not element.dest.startswith("#"):
                    links.append(element.dest)
            case _:
                if hasattr(element, "children"):
                    for child in element.children:
                        _find_links(child)

    _find_links(element)
    return links


def extract_links(file_path: str, include_internal=False) -> List[str]:
    """Extract all links from a Markdown file. Future: Include textual and section context."""

    with open(file_path, "r") as file:
        content = file.read()
        document = marko.parse(content)
        return _tree_links(document, include_internal)


def _tree_bullet_points(element):
    bullet_points = []

    def _find_bullet_points(element):
        if isinstance(element, ListItem):
            bullet_points.append(element.children[0].children[0].children.strip())  # type: ignore
        elif hasattr(element, "children"):
            for child in element.children:
                _find_bullet_points(child)

    _find_bullet_points(element)
    return bullet_points


def extract_bullet_points(content: str) -> List[str]:
    """Extract list item values from a Markdown file."""

    document = marko.parse(content)
    return _tree_bullet_points(document)


def _type_from_heading(heading: Heading) -> str:
    if heading.level in [1, 2, 3, 4, 5, 6]:
        return f"h{heading.level}"
    else:
        raise ValueError(f"Unsupported heading: {heading}: level {heading.level}")


def _extract_text(element):
    if isinstance(element, str):
        return element
    return "".join(_extract_text(child) for child in element.children)
