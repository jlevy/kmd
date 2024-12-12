"""
Kyrm Codes
==========

This is a draft schema for "Kyrm codes" for terminal applications.

The idea of Kyrm codes is to enable terminals and command-line applications
to provide a richer user interface, blending terminal and basic web-style UI
elements. By incorporating these codes, rather than just plain text, advanced
terminals can display links, tooltips, buttons, and interactive input elements.

This schema specifies a method to encode UI elements as structured data and
transmit them through OSC (Operating System Command) codes. These codes are
named after Kyrm, a new terminal app, but could be used with any application.

These codes are backward compatible with existing terminals, which will either
ignore these codes or render them as links.

UI elements such as tooltips, buttons, popovers, and input fields are defined
via a simple JSON schema, specified here using Pydantic. These elements
are serialized in either of two ways:

- Directly as JSON
- As "kui://" URIs (called here KRIs)

The terminal or any other front-end code parses and renders these elements
encoded in these formats.

JSON and KRI formats are each useful in different contexts. Some UI elements
are attached to text in the terminal, while other times, an application may
just want to create a new UI element.

If the UI element is attached to text, such as a tooltip or a button, OSC 8
hyperlinks are used encode the KRI for the desired UI element. Note regular
URLs are a special case of KRIs so can be used as normal in a terminal that
supports OSC 8 links, so this scheme simply augments standard terminal links.

If the UI element is standalone, such as a button or input field, we use a new,
previously unused code, OSC 77. We've picked this code since it's not used by
other applications and is ignored by terminals that don't support it.

By adding these two codes to terminal text, it's possible to create a flexible
system for displaying enriched UIs within terminal applications that support
them. This approach allows incrementally adding rich UIs to text applications
while not breaking functionality in existing terminals.

See also:
https://github.com/Alhadis/OSC8-Adoption
https://github.com/chromium/hterm/blob/main/doc/ControlSequences.md#OSC
https://www.ethanheilman.com/x/28/index.html
"""

from enum import Enum
from html import escape
from typing import Annotated, Dict, List, Literal, Optional, Self, Union
from urllib.parse import parse_qs, quote, urlencode, urlparse

from pydantic import BaseModel, Field, model_validator, TypeAdapter
from rich.style import Style
from rich.text import Text

from kmd.shell_tools.osc_tools import osc_code

KUI_PROTOCOL = "kui:"
"""The "protocol" portion of Kyrm URIs."""

KUI_SCHEME = f"{KUI_PROTOCOL}//"
"""The Kyrm URI scheme for embedding UI elements into links."""

KUI_OSC = "77"
"""A lucky OSC code not used by other applications."""

KUI_VERSION = 0
"""Version of the Kyrm codes format. Update when we make breaking changes."""


class KriType(str, Enum):
    """Types of rich URIs."""

    url = "url"
    tooltip = "tooltip"
    button = "button"
    popover = "popover"
    action = "action"
    notification = "notification"

    @property
    def kui_prefix(self) -> str:
        if self == KriType.url:
            return ""
        else:
            return f"{KUI_SCHEME}{self.value}"


class Kri(BaseModel):
    """
    A KRI is a "Kyrm URI" conveying rich metadata for UI elements, of the form:
    `kui://kri_type?k1=v1&k2=v2&...`.
    """

    kri_type: KriType = Field(
        ..., description="The type of the KRI is the path portion of the URI."
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="KRI metadata is the query string of the URI."
    )
    url: Optional[str] = Field(
        default=None,
        description="Just the URL, if this is a plain URL, or None if it's another KRY type.",
    )

    @model_validator(mode="after")
    def validate_url_consistency(self) -> Self:
        if self.kri_type == KriType.url and self.url is None:
            raise ValueError("URL is required for type 'url'")
        if self.kri_type != KriType.url and self.url is not None:
            raise ValueError("URL must be None unless of type 'url'")
        return self

    @classmethod
    def from_url(cls, url: str) -> Self:
        return cls(kri_type=KriType.url, url=url)

    @classmethod
    def tooltip(cls, text: str) -> Self:
        """
        Example: kui://tooltip?text=My%20Tooltip
        """
        return cls(kri_type=KriType.tooltip, metadata={"text": text})

    @classmethod
    def button(cls, text: str, action: str, value: str) -> Self:
        """
        Example: kui://button?text=Click%20Me&action=paste&value=ls%20-l
        """
        return cls(
            kri_type=KriType.button,
            metadata={"text": text, "action": action, "value": value},
        )

    @classmethod
    def popover(cls, url: str) -> Self:
        """
        Example: kui://popover?url=https%3A%2F%2Fexample.com
        """
        return cls(kri_type=KriType.popover, metadata={"url": url})

    @classmethod
    def action(cls, action: str, value: str) -> Self:
        """
        Example: kui://action?action=paste&value=ls%20-l
        """
        return cls(
            kri_type=KriType.action,
            metadata={"action": action, "value": value},
        )

    @classmethod
    def notification(cls, text: str) -> Self:
        """
        Example: kui://notification?text=Hello%20World
        """
        return cls(kri_type=KriType.notification, metadata={"text": text})

    @classmethod
    def parse(cls, uri_str: str) -> Self:
        """
        Parse a URI string into a Kri.
        """
        # Parse plain URLs.
        if uri_str.startswith(("http://", "https://")):
            return cls(kri_type=KriType.url, url=uri_str)

        # Parse kui:// URIs into type and metadata.
        if uri_str.startswith(KUI_SCHEME):
            parsed = urlparse(uri_str)
            try:
                uri_type = KriType(parsed.netloc)
            except ValueError:
                raise ValueError(f"Unrecognized {KUI_SCHEME} URI: {uri_str}")
            metadata = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            return cls(kri_type=uri_type, metadata=metadata)
        raise ValueError(f"Invalid URI scheme: {uri_str}")

    @property
    def uri_str(self) -> str:
        """
        The full URI, including the type and metadata.
        Note that we use cautious URL encoding, i.e. %20 and not + for encodingspaces.
        """
        if self.kri_type == KriType.url:
            assert self.url is not None
            return self.url
        else:
            return f"{self.kri_type.kui_prefix}?{urlencode(self.metadata, quote_via=quote)}"

    def __str__(self) -> str:
        return self.uri_str


class Link(BaseModel):
    """
    A text link with a URL or KRI and link text. Serializable as an OSC 8
    hyperlink.
    """

    kri: Kri
    link_text: str

    @property
    def osc8(self) -> str:
        from kmd.shell_tools.osc_tools import osc8_link

        return osc8_link(self.kri.uri_str, self.link_text)

    def as_rich(self, style: str | Style = "") -> Text:
        return Text.from_ansi(self.osc8, style=style)

    def as_html(self) -> str:
        return f'<a href="{escape(self.kri.uri_str, quote=True)}">{escape(self.link_text)}</a>'

    def as_json(self) -> str:
        return self.model_dump_json()


class ElementType(str, Enum):
    text_tooltip = "text_tooltip"
    link_tooltip = "link_tooltip"
    iframe_tooltip = "iframe_tooltip"

    iframe_popover = "iframe_popover"

    chat_output = "chat_output"
    chat_input = "chat_input"

    button = "button"
    multiple_choice = "multiple_choice"


class UIActionType(str, Enum):
    paste = "paste"
    run_command = "run_command"
    open_iframe_popover = "open_iframe_popover"


class UIAction(BaseModel):
    """
    An action triggered by a UI element, such as pasting text or running a command.
    """

    action_type: UIActionType = Field(..., description="Action element_type.")
    value: str = Field(..., description="Action value.")

    def to_kri(self) -> str:
        return Kri.action(self.action_type, self.value).uri_str


class Position(BaseModel):
    """
    Position hints for UI elements.
    """

    x: int = Field(..., description="X position.")
    y: int = Field(..., description="Y position.")


class Dimensions(BaseModel):
    """
    Dimensions hints for UI elements.
    """

    width: int = Field(..., description="Width.")
    height: int = Field(..., description="Height.")


class DisplayHints(BaseModel):
    """
    Hints for UI elements.
    """

    position: Optional[Position] = Field(default=None, description="Position.")
    dimensions: Optional[Dimensions] = Field(default=None, description="Dimensions.")


class UIElement(BaseModel):
    """
    Base class for all UI elements.
    """

    element_type: ElementType
    kui_version: int = Field(default=KUI_VERSION, description="Kyrm code version")
    hints: Optional[DisplayHints] = Field(default=None, description="Display hints.")

    @model_validator(mode="after")
    def validate_version(self) -> Self:
        if self.kui_version < KUI_VERSION:
            raise ValueError(
                f"Incompatible Kyrm code version: expected {KUI_VERSION}, got {self.kui_version}"
            )
        return self

    def as_json(self) -> str:
        """
        Convert to a JSON string.
        """
        return self.model_dump_json()

    def as_osc(self) -> str:
        """
        Convert to an OSC 77 code.
        """
        return osc_code(KUI_OSC, self.model_dump_json())


class InputElement(UIElement):
    """
    Base for input elements.
    """


class TextTooltip(UIElement):
    """
    A simple text tooltip.
    """

    element_type: Literal[ElementType.text_tooltip] = ElementType.text_tooltip
    text: str = Field(..., description="Tooltip text.")

    def to_kri(self) -> str:
        return Kri.tooltip(self.text).uri_str


class LinkTooltip(UIElement):
    """
    A tooltip with info about a URL. Typically this would be a tooltip like with a
    preview of the page or the title and description of the page.
    """

    element_type: Literal[ElementType.link_tooltip] = ElementType.link_tooltip
    url: str = Field(..., description="Tooltip URL.")

    def to_kri(self) -> str:
        return self.url


class IframeTooltip(UIElement):
    """
    A tooltip with an iframe.
    """

    element_type: Literal[ElementType.iframe_tooltip] = ElementType.iframe_tooltip
    url: str = Field(..., description="Tooltip iframe URL.")

    def to_kri(self) -> str:
        return self.url


class IframePopover(UIElement):
    """
    A popover with an iframe.
    """

    element_type: Literal[ElementType.iframe_popover] = ElementType.iframe_popover
    url: str = Field(..., description="Popover iframe URL.")

    def to_kri(self) -> str:
        return Kri.popover(self.url).uri_str


class ChatOutput(UIElement):
    """
    Chat-like output or response element.
    """

    element_type: Literal[ElementType.chat_output] = ElementType.chat_output
    text: str = Field(..., description="Chat text.")


class ChatInput(UIElement):
    """
    Chat-like input element.
    """

    element_type: Literal[ElementType.chat_input] = ElementType.chat_input
    prompt: str = Field(..., description="Initial prompt.")


class Button(UIElement):
    """
    A clickable button.
    """

    element_type: Literal[ElementType.button] = ElementType.button
    text: str = Field(..., description="Button label.")
    action: UIAction = Field(..., description="Button action.")

    def to_kri(self) -> str:
        return Kri.button(self.text, self.action.action_type, self.action.value).uri_str


class MultipleChoice(InputElement):
    """
    Multiple-choice input element.
    """

    element_type: Literal[ElementType.multiple_choice] = ElementType.multiple_choice
    options: List[str] = Field(..., description="Choice options.")


UIElementUnion = Annotated[
    Union[
        TextTooltip,
        LinkTooltip,
        IframeTooltip,
        Button,
        MultipleChoice,
        ChatOutput,
        ChatInput,
        IframePopover,
    ],
    Field(discriminator="element_type"),
]


## Tests


def test_parsing():
    tooltip_json = '{"element_type": "text_tooltip", "text": "Hello", "version": "kyrm.v0"}'
    tooltip = TextTooltip.model_validate_json(tooltip_json)
    assert tooltip.element_type == ElementType.text_tooltip
    assert tooltip.text == "Hello"


def test_examples():

    kri = Kri.parse("kui://tooltip?text=Tooltip%20text")
    assert kri.kri_type == KriType.tooltip
    assert kri.metadata == {"text": "Tooltip text"}

    tooltip_link = Link(kri=kri, link_text="Link text")
    assert tooltip_link.as_html() == '<a href="kui://tooltip?text=Tooltip%20text">Link text</a>'

    button = Button(
        text="Click me",
        action=UIAction(action_type=UIActionType.paste, value="ls"),
    )

    popover_element = IframePopover(
        url="https://example.com",
        hints=DisplayHints(
            position=Position(x=10, y=10), dimensions=Dimensions(width=100, height=100)
        ),
    )

    print("\ntooltip_link:")
    print("\n".join([tooltip_link.as_html(), repr(tooltip_link.osc8)]))

    print("\nbutton:")
    print("\n".join([button.as_json(), repr(button.as_osc())]))

    print("\npopover_element:")
    print(
        "\n".join(
            [
                popover_element.as_json(),
                repr(popover_element.as_osc()),
                popover_element.to_kri(),
            ]
        )
    )

    # Test round-tripping.
    element_parser = TypeAdapter(UIElementUnion)
    for element in [button, popover_element]:
        parsed = element_parser.validate_json(element.as_json())
        assert parsed.element_type == element.element_type
        assert parsed.as_json() == element.as_json()
        assert parsed.as_osc() == element.as_osc()
