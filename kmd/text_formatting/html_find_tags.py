from dataclasses import dataclass
from typing import List, Optional

import regex

from kmd.util.obj_utils import abbreviate_obj


@dataclass(frozen=True)
class TagMatch:
    tag_name: str
    start_offset: int
    end_offset: int
    attribute_name: Optional[str]
    attribute_value: Optional[str]
    inner_text: str

    def __str__(self):
        return abbreviate_obj(self)


def html_find_tag(
    html_string: str,
    tag_name: Optional[str] = None,
    attr_name: Optional[str] = None,
    attr_value: Optional[str] = None,
) -> List[TagMatch]:
    """
    Find all HTML elements matching the specified tag name, attribute name, and attribute
    value. If any are not specified, any tag, attribute, or value will be matched.
    """
    # Build the regex pattern parts.
    tag_pattern = tag_name if tag_name else r"\w+"
    attr_pattern = ""
    if attr_name:
        if attr_value:
            attr_pattern = rf'\b{attr_name}=["\']{regex.escape(attr_value)}["\']'
        else:
            attr_pattern = rf'\b{attr_name}=["\'](?:[^"\']+)["\']'

    full_pattern = rf"<({tag_pattern})[^>]*{attr_pattern}[^>]*>(.*?)</\1>"
    compiled_pattern = regex.compile(
        full_pattern,
        regex.IGNORECASE | regex.DOTALL,
    )

    matches: List[TagMatch] = []
    for match in compiled_pattern.finditer(html_string):
        matched_tag = match.group(1)
        inner_text = match.group(2)
        start_offset = match.start()
        end_offset = match.end()

        # Extract attribute value if attr_name is provided and attr_value is not specified.
        if attr_name and not attr_value:
            attr_match = regex.search(rf'\b{attr_name}=["\']([^"\']+)["\']', match.group(0))
            attribute_value = attr_match.group(1) if attr_match else None
        else:
            attribute_value = attr_value

        matches.append(
            TagMatch(
                tag_name=matched_tag,
                start_offset=start_offset,
                end_offset=end_offset,
                attribute_name=attr_name,
                attribute_value=attribute_value,
                inner_text=inner_text,
            )
        )
    return matches


def html_extract_attribute_value(attr_name: str):
    """
    Extract the value of an attribute from a string with an HTML tag.
    """
    attribute_re = regex.compile(rf'(?:<\w+[^>]*\s)?{attr_name}=[\'"]([^\'"]+)[\'"][^>]*>')

    def extractor(html_string: str):
        match = attribute_re.search(html_string)
        return match.group(1) if match else None

    return extractor


## Tests


def test_html_find_tag():
    html_string = """
    <div class="container">
        <p id="intro">Hello, World!</p>
        <span data-info="test">Sample Text</span>
        <p>Another paragraph</p>
    </div>
    """
    matches = html_find_tag(html_string, tag_name="p")
    assert len(matches) == 2
    assert matches[0].tag_name == "p"
    assert matches[0].inner_text.strip() == "Hello, World!"
    assert matches[1].inner_text.strip() == "Another paragraph"

    matches_attr = html_find_tag(html_string, attr_name="data-info")
    assert len(matches_attr) == 1
    assert matches_attr[0].tag_name == "span"
    assert matches_attr[0].attribute_name == "data-info"
    assert matches_attr[0].attribute_value == "test"
    assert matches_attr[0].inner_text.strip() == "Sample Text"
