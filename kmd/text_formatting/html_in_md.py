"""
Formatting of Markdown with a small set of known HTML classes. We do this directly
ourselves to keep the HTML very minimal, control whitespace, and to avoid any
confusions of using full HTML escaping (like unnecessary &quot;s etc.)
"""

import re
from typing import Callable, Dict, List, Optional

from kmd.model.doc_elements import DATA_SPEAKER_ID, DATA_TIMESTAMP, SPEAKER_LABEL


def escape_md_html(s: str, safe: bool = False) -> str:
    """
    Escape a string for Markdown with HTML. Don't escape single and double quotes.
    """
    if safe:
        return s
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    return s


def escape_attribute(s: str) -> str:
    """
    Escape a string for use as an HTML attribute. Escape single and double quotes.
    """
    s = escape_md_html(s)
    s = s.replace('"', "&quot;")
    s = s.replace("'", "&#39;")
    return s


ClassNames = str | List[str]


def tag_with_attrs(
    tag: str,
    text: Optional[str],
    class_name: Optional[ClassNames] = None,
    attrs: Optional[Dict[str, str]] = None,
    safe: bool = False,
    padding: Optional[str] = None,
) -> str:
    class_value = ""
    if class_name is not None:
        if isinstance(class_name, str):
            class_value = class_name
        elif isinstance(class_name, list):
            class_value = " ".join(class_name)
        else:
            raise ValueError(f"Expected a string or list of class names but got: {class_name}")
    attr_str = f' class="{escape_attribute(class_value)}"' if class_value else ""
    if attrs:
        attr_str += "".join(f' {k}="{escape_attribute(v)}"' for k, v in attrs.items())
    # Default padding for div and p tags.
    if text is None:
        return f"<{tag}{attr_str} />"
    else:
        content = escape_md_html(text, safe)
        if padding is None:
            padding = "\n" if tag in ["div", "p"] else ""
        if padding:
            content = content.strip("\n")
            if not content:
                padding = ""
        return f"<{tag}{attr_str}>{padding}{content}{padding}</{tag}>"


def html_span(
    text: str,
    class_name: Optional[ClassNames] = None,
    attrs: Optional[Dict[str, str]] = None,
    safe: bool = False,
) -> str:
    """
    Write a span tag for use in Markdown, with the given text and optional class and attributes.
    """
    return tag_with_attrs("span", text, class_name, attrs, safe)


def html_div(
    text: str,
    class_name: Optional[ClassNames] = None,
    attrs: Optional[Dict[str, str]] = None,
    safe: bool = False,
    padding: Optional[str] = None,
) -> str:
    """
    Write a div tag for use in Markdown, with the given text and optional class and attributes.
    """
    return tag_with_attrs("div", text, class_name, attrs, safe, padding)


def html_timestamp_span(text: str, timestamp: float, safe: bool = False) -> str:
    return html_span(text, attrs={DATA_TIMESTAMP: f"{timestamp:.2f}"}, safe=safe)


def html_speaker_id_span(text: str, speaker_id: str, safe: bool = False) -> str:
    return html_span(text, class_name=SPEAKER_LABEL, attrs={DATA_SPEAKER_ID: speaker_id}, safe=safe)


def html_a(text: str, href: str, safe: bool = False) -> str:
    text = escape_md_html(text, safe)
    return f'<a href="{href}">{text}</a>'


def html_img(
    src: str,
    alt: str,
    class_name: Optional[ClassNames] = None,
    attrs: Optional[Dict[str, str]] = None,
    safe: bool = False,
) -> str:
    img_attrs = {"src": src, "alt": alt}
    if attrs:
        img_attrs.update(attrs)
    return tag_with_attrs("img", None, class_name, img_attrs, safe=safe)


def html_join_blocks(*blocks: str) -> str:
    """
    Join block elements, with double newlines for better Markdown compatibility.
    """
    return "\n\n".join(block.strip("\n") for block in blocks)


Wrapper = Callable[[str], str]
"""Wraps a string to identify it in some way."""


def identity_wrapper(text: str) -> str:
    return text


def _check_class_name(class_name: Optional[str]) -> None:
    if class_name and not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", class_name):
        raise ValueError(f"Expected a valid CSS class name but got: '{class_name}'")


def div_wrapper(
    class_name: Optional[str] = None, safe: bool = True, padding: Optional[str] = "\n\n"
) -> Wrapper:
    _check_class_name(class_name)

    def div_wrapper_func(text: str) -> str:
        return html_div(text, class_name, safe=safe, padding=padding)

    return div_wrapper_func


def span_wrapper(class_name: Optional[str] = None, safe: bool = True) -> Wrapper:
    _check_class_name(class_name)

    def span_wrapper_func(text: str) -> str:
        return html_span(text, class_name, safe=safe)

    return span_wrapper_func


## Tests


def test_html():
    assert escape_md_html("&<>") == "&amp;&lt;&gt;"
    assert escape_attribute("\"'&<>") == "&quot;&#39;&amp;&lt;&gt;"
    assert (
        tag_with_attrs("span", "text", class_name="foo", attrs={"id": "a"})
        == '<span class="foo" id="a">text</span>'
    )
    assert (
        html_span("text", class_name="foo", attrs={"id": "a"})
        == '<span class="foo" id="a">text</span>'
    )
    assert (
        html_div("text 1<2", class_name="foo", attrs={"id": "a"})
        == '<div class="foo" id="a">\ntext 1&lt;2\n</div>'
    )
    assert html_div("text") == "<div>\ntext\n</div>"
    assert html_timestamp_span("text", 123.456) == '<span data-timestamp="123.46">text</span>'


def test_div_wrapper():
    safe_wrapper = div_wrapper(class_name="foo")
    assert safe_wrapper("<div>text</div>") == '<div class="foo">\n\n<div>text</div>\n\n</div>'

    unsafe_wrapper = div_wrapper(class_name="foo", safe=False)
    assert (
        unsafe_wrapper("<div>text</div>")
        == '<div class="foo">\n\n&lt;div&gt;text&lt;/div&gt;\n\n</div>'
    )
