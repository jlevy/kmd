from dataclasses import field
from enum import Enum
from typing import Dict, Optional
from urllib.parse import parse_qs, urlencode

from pydantic.dataclasses import dataclass
from rich.style import Style
from rich.text import Text

from kmd.config.logger import get_logger
from kmd.shell_tools.osc_tools import osc8_link


log = get_logger(__name__)

UI_SCHEME = "ui://"


class RichUriType(Enum):
    url = "url"
    tooltip = "tooltip"
    button = "button"
    command = "command"

    @property
    def prefix(self) -> str:
        if self == RichUriType.url:
            return ""
        else:
            return f"ui://{self.value}"


@dataclass(frozen=True)
class RichUri:
    """
    A URI that can convey additional rich metadata in the terminal, such as
    a tooltip or a button.

    Supported types:

    Any http or https URL:
        https://example.com

    Tooltips, buttons, commands, or other widget types:
        ui://tooltip?text=Some%20Tooltip
        ui://button?text=Press%20Me
        ui://command?text=Some%20Tooltip

    After the type path, are URL-style query parameters. It's recommended to use
    `text` for the primary value, but other values can be included as needed, such as
        ui://button?text=Press%20Me&style=primary
    """

    type: RichUriType

    url_text: Optional[str] = None
    """The URL, if this is a RichUriType.url."""

    metadata: Dict[str, str] = field(default_factory=dict)
    """Other metadata values."""

    @property
    def uri_str(self) -> str:
        """
        The full URI, including the protocol prefix.
        """
        if self.type == RichUriType.url:
            if self.url_text is None:
                raise ValueError("url_text is required for RichUriType.url")
            return self.url_text
        else:
            return f"{self.type.prefix}?{urlencode(self.metadata)}"

    @classmethod
    def tooltip(cls, text: str) -> "RichUri":
        return cls(type=RichUriType.tooltip, metadata={"text": text})

    @classmethod
    def button(cls, text: str) -> "RichUri":
        return cls(type=RichUriType.button, metadata={"text": text})

    @classmethod
    def parse(cls, uri_str: str) -> "RichUri":
        """
        Parse a URL or ui:// URI into its components.
        """
        if uri_str.startswith(("http://", "https://")):
            return cls(type=RichUriType.url, url_text=uri_str)

        if uri_str.startswith(UI_SCHEME):
            raise ValueError(f"Invalid URI scheme: {uri_str}")

        # Remove ui:// prefix and split into path and query.
        uri_without_scheme = uri_str[len(UI_SCHEME) :]
        path_parts = uri_without_scheme.split("?", 1)
        type_str, query_str = path_parts

        try:
            uri_type = RichUriType(type_str)
        except ValueError:
            raise ValueError(f"Invalid RichUriType: {type_str}")

        query_params = parse_qs(query_str)
        metadata = {k: v[0] for k, v in query_params.items()}

        return cls(type=uri_type, metadata=metadata)


@dataclass(frozen=True)
class RichLink:
    uri: RichUri
    link_text: str

    def osc8_link(self) -> str:
        return osc8_link(self.uri.uri_str, self.link_text)

    def rich_link(self, style: str | Style = "") -> Text:
        return Text.from_ansi(self.osc8_link(), style=style)
