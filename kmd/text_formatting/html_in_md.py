"""
Formatting of Markdown with a small set of known HTML classes. We do this directly
ourselves to keep the HTML very minimal, control whitespace, and to avoid any
confusions of using full HTML escaping (like unnecessary &quot;s etc.)
"""

from typing import Callable, Optional, Dict


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


def tag_with_attrs(
    tag: str,
    text: str,
    cls: Optional[str] = None,
    attrs: Optional[Dict[str, str]] = None,
    safe: bool = False,
) -> str:
    attr_str = f' class="{escape_attribute(cls)}"' if cls else ""
    if attrs:
        attr_str += "".join(f' {k}="{escape_attribute(v)}"' for k, v in attrs.items())
    if tag in ["div", "p"]:
        br = "\n"
    else:
        br = ""
    return f"<{tag}{attr_str}>{br}{escape_md_html(text, safe)}{br}</{tag}>"


CITATION = "citation"
DESCRIPTION = "description"
SUMMARY = "summary"
FULL_TEXT = "full-text"

DATA_TIMESTAMP = "data-timestamp"


def html_span(
    text: str,
    class_name: Optional[str] = None,
    attrs: Optional[Dict[str, str]] = None,
    safe: bool = False,
) -> str:
    return tag_with_attrs("span", text, class_name, attrs, safe)


def html_div(
    text: str,
    class_name: Optional[str] = None,
    attrs: Optional[Dict[str, str]] = None,
    safe: bool = False,
) -> str:
    return tag_with_attrs("div", text, class_name, attrs, safe)


def html_timestamp_span(text: str, timestamp: float, safe: bool = False) -> str:
    return html_span(text, attrs={DATA_TIMESTAMP: f"{timestamp:.2f}"}, safe=safe)


def html_a(text: str, href: str, safe: bool = False) -> str:
    text = escape_md_html(text, safe)
    return f'<a href="{href}">{text}</a>'


Wrapper = Callable[[str], str]
"""Wraps a string to identify it in some way."""


def identity_wrapper(text: str) -> str:
    return text


def div_wrapper(class_name: Optional[str] = None, safe: bool = True) -> Wrapper:
    def div_wrapper_func(text: str) -> str:
        return html_div(text, class_name, safe=safe)

    return div_wrapper_func


def span_wrapper(class_name: Optional[str] = None, safe: bool = True) -> Wrapper:
    def span_wrapper_func(text: str) -> str:
        return html_span(text, class_name, safe=safe)

    return span_wrapper_func


## Tests


def test_html():
    assert escape_md_html("&<>") == "&amp;&lt;&gt;"
    assert escape_attribute("\"'&<>") == "&quot;&#39;&amp;&lt;&gt;"
    assert (
        tag_with_attrs("span", "text", cls="foo", attrs={"id": "a"})
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
    assert safe_wrapper("<div>text</div>") == '<div class="foo">\n<div>text</div>\n</div>'

    unsafe_wrapper = div_wrapper(class_name="foo", safe=False)
    assert (
        unsafe_wrapper("<div>text</div>")
        == '<div class="foo">\n&lt;div&gt;text&lt;/div&gt;\n</div>'
    )