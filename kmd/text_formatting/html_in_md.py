"""
Formatting of Markdown with a small set of known HTML classes. We do this directly
ourselves to keep the HTML very minimal, control whitespace, and to avoid any
confusions of using full HTML escaping (like unnecessary &quot;s etc.)
"""

from typing import Optional, Dict


def escape_md_html(s: str) -> str:
    """
    Escape a string for Markdown with HTML. Don't escape single and double quotes.
    """
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
    tag: str, text: str, cls: Optional[str] = None, attrs: Optional[Dict[str, str]] = None
) -> str:
    attr_str = f' class="{escape_attribute(cls)}"' if cls else ""
    if attrs:
        attr_str += "".join(f' {k}="{escape_attribute(v)}"' for k, v in attrs.items())
    if tag in ["div", "p"]:
        br = "\n"
    else:
        br = ""
    return f"<{tag}{attr_str}>{br}{escape_md_html(text)}{br}</{tag}>"


def html_span(text: str, cls: Optional[str] = None, attrs: Optional[Dict[str, str]] = None) -> str:
    return tag_with_attrs("span", text, cls, attrs)


def html_div(text: str, cls: Optional[str] = None, attrs: Optional[Dict[str, str]] = None) -> str:
    return tag_with_attrs("div", text, cls, attrs)


CITATION = "citation"
DESCRIPTION = "description"
SUMMARY = "summary"
TRANSCRIPT = "transcript"

DATA_TIMESTAMP = "data-timestamp"


def html_citation(citation: str) -> str:
    return html_span(citation, CITATION)


def html_description(text: str) -> str:
    return html_span(text, DESCRIPTION)


def html_summary(text: str) -> str:
    return html_span(text, SUMMARY)


def html_transcript(text: str) -> str:
    return html_span(text, TRANSCRIPT)


def html_timestamp_span(text: str, timestamp: float) -> str:
    return html_span(text, attrs={DATA_TIMESTAMP: f"{timestamp:.2f}"})


def html_a(text: str, href: str) -> str:
    return f'<a href="{href}">{text}</a>'


## Tests


def test_all_functions():
    assert escape_md_html("&<>") == "&amp;&lt;&gt;"
    assert escape_attribute("\"'&<>") == "&quot;&#39;&amp;&lt;&gt;"
    assert (
        tag_with_attrs("span", "text", cls="foo", attrs={"id": "a"})
        == '<span class="foo" id="a">text</span>'
    )
    assert html_span("text", cls="foo", attrs={"id": "a"}) == '<span class="foo" id="a">text</span>'
    assert (
        html_div("text 1<2", cls="foo", attrs={"id": "a"})
        == '<div class="foo" id="a">\ntext 1&lt;2\n</div>'
    )
    assert html_citation("citation") == '<span class="citation">citation</span>'
    assert html_description("description") == '<span class="description">description</span>'
    assert html_timestamp_span("text", 123.456) == '<span data-timestamp="123.46">text</span>'
