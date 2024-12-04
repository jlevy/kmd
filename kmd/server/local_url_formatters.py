from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from rich.text import Text

from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_HINT, COLOR_LINK
from kmd.errors import InvalidState
from kmd.model.args_model import fmt_loc

from kmd.model.paths_model import StorePath
from kmd.server.rich_terminal_codes import RichUri
from kmd.shell_tools.osc_tools import osc8_link_rich
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


class LinkFormatter(ABC):
    """
    Base class for adding URL links to values.
    """

    @abstractmethod
    def tooltip_link(self, text: str, tooltip: Optional[str] = None) -> Text:
        pass

    @abstractmethod
    def path_link(self, path: Path, link_text: str) -> Text:
        pass

    @abstractmethod
    def command_link(self, command_str: str) -> Text:
        pass


class PlaintextFormatter(LinkFormatter):
    """
    A plaintext formatter that doesn't use links.
    """

    def tooltip_link(self, text: str, tooltip: Optional[str] = None) -> Text:
        return Text(text)

    def path_link(self, path: Path, link_text: str) -> Text:
        return Text(fmt_loc(link_text))

    def command_link(self, command_str: str) -> Text:
        return Text.assemble(Text("`", style=COLOR_HINT), command_str, Text("`", style=COLOR_HINT))


class DefaultFormatter(PlaintextFormatter):
    """
    A formatter that adds OSC8 links to the local server.
    """

    def tooltip_link(self, text: str, tooltip: Optional[str] = None) -> Text:
        if tooltip:
            return osc8_link_rich(RichUri.tooltip(tooltip).uri_str, text)
        else:
            return Text(text)

    def path_link(self, path: Path, link_text: str) -> Text:
        from kmd.server.server_routes import local_url

        url = local_url.view_file(path)
        link = osc8_link_rich(url, link_text)
        return link

    def command_link(self, command_str: str) -> Text:
        from kmd.server.server_routes import local_url

        url = local_url.explain(text=command_str)
        return Text.assemble(
            Text("`", style=COLOR_HINT),
            osc8_link_rich(url, command_str, style=COLOR_LINK),
            Text("`", style=COLOR_HINT),
        )

    def __str__(self):
        return "DefaultFormatter()"


class WorkspaceUrlFormatter(DefaultFormatter):
    """
    A formatter that also has workspace context so can add workspace-specific links.
    """

    def __init__(self, ws_name: str):
        self.ws_name = ws_name

    def path_link(self, path: Path, link_text: str) -> Text:
        if isinstance(path, StorePath):
            from kmd.server.server_routes import local_url

            url = local_url.view_item(store_path=path, ws_name=self.ws_name)
            link = osc8_link_rich(url, link_text)
            return link
        else:
            return super().path_link(path, link_text)

    def __str__(self):
        return f"WorkspaceUrlFormatter(ws_name={self.ws_name})"


@contextmanager
def local_url_formatter(ws_name: Optional[str] = None):
    """
    Context manager to make it easy to format store paths with links to the local
    server for more info. If ws_name is None, use the default formatter.
    """
    try:
        ws_name = current_workspace().name
        fmt = WorkspaceUrlFormatter(ws_name)
    except InvalidState:
        fmt = DefaultFormatter()

    log.info("Using %s", fmt)
    try:
        yield fmt
    finally:
        pass
