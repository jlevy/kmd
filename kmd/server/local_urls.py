from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from rich.text import Text

from kmd.config.logger import get_logger
from kmd.config.settings import global_settings
from kmd.config.text_styles import COLOR_HINT, COLOR_LINK
from kmd.errors import InvalidState
from kmd.model.args_model import fmt_loc
from kmd.model.paths_model import StorePath
from kmd.server.server_routes import Route
from kmd.shell_tools.osc_tools import osc8_link_rich
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


def local_url(path: str, **params: Optional[str]) -> str:
    """
    URL to content on the local server.
    """
    settings = global_settings()
    path = path.strip("/")
    url = f"http://{settings.local_server_host}:{settings.local_server_port}/{path}"
    if params:
        query_params = {k: v for k, v in params.items() if v is not None}
        if query_params:
            query_string = urlencode(query_params)
            url += f"?{query_string}"
    return url


class LinkFormatter(ABC):
    """
    Base class for adding URL links to values.
    """

    @abstractmethod
    def path_link(self, path: Path) -> Text:
        pass

    @abstractmethod
    def command_link(self, command_str: str) -> Text:
        pass


class PlaintextFormatter(LinkFormatter):
    """
    A plaintext formatter that doesn't use links.
    """

    def path_link(self, path: Path) -> Text:
        return Text(fmt_loc(path))

    def command_link(self, command_str: str) -> Text:
        return Text.assemble(Text("`", style=COLOR_HINT), command_str, Text("`", style=COLOR_HINT))


class DefaultFormatter(PlaintextFormatter):
    """
    A formatter that uses OSC8 links.
    """

    def path_link(self, path: Path) -> Text:
        return super().path_link(path)  # FIXME: Add links to other paths.

    def command_link(self, command_str: str) -> Text:
        url = local_url(Route.explain, text=command_str)
        return Text.assemble(
            Text("`", style=COLOR_HINT),
            osc8_link_rich(url, command_str, style=COLOR_LINK),
            Text("`", style=COLOR_HINT),
        )

    def __str__(self):
        return "NoWorkspaceUrlFormatter()"


class WorkspaceUrlFormatter(DefaultFormatter):
    """
    A formatter that also has workspace context so can add workspace-specific links.
    """

    def __init__(self, ws_name: str):
        self.ws_name = ws_name

    def path_link(self, path: Path) -> Text:
        # Only link StorePaths. Avoiding linking to all system paths seems like
        # a simple way to avoid a bunch of security issues.
        if isinstance(path, StorePath):
            url = local_url(Route.view_item, store_path=path.display_str(), ws_name=self.ws_name)
            link = osc8_link_rich(url, fmt_loc(path))
            return link
        else:
            return super().path_link(path)

    def __str__(self):
        return f"WorkspaceUrlFormatter(ws_name={self.ws_name})"


@contextmanager
def ws_formatter(ws_name: Optional[str] = None):
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
