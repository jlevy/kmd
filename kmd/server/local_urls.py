from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from rich.text import Text

from kmd.config.logger import get_logger
from kmd.config.settings import global_settings
from kmd.config.text_styles import COLOR_LINK
from kmd.model.args_model import fmt_loc
from kmd.model.paths_model import StorePath
from kmd.server.server_routes import Route
from kmd.shell_tools.osc_tools import osc8_link

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
    def path_link(self, path: Path) -> str:
        pass

    @abstractmethod
    def command_link(self, command_str: str) -> Text:
        pass


class NoLinkFormatter(LinkFormatter):
    def path_link(self, path: Path) -> str:
        return fmt_loc(path)

    def command_link(self, command_str: str) -> Text:
        return Text.assemble("`", command_str, "`")


class LocalWsUrlFormatter(LinkFormatter):
    def __init__(self, ws_name: str):
        self.ws_name = ws_name

    def view_item_url(self, store_path: StorePath) -> str:
        return local_url(Route.view_item, store_path=store_path.display_str(), ws_name=self.ws_name)

    def read_item_url(self, store_path: StorePath) -> str:
        return local_url(Route.read_item, store_path=store_path.display_str(), ws_name=self.ws_name)

    def explain_url(self, text: str) -> str:
        return local_url(Route.explain, text=text, ws_name=self.ws_name)

    def path_link(self, path: Path) -> str:
        # Only link StorePaths. Avoiding linking to all system paths seems like
        # a simple way to avoid a bunch of security issues.
        if isinstance(path, StorePath):
            link = osc8_link(self.view_item_url(path), fmt_loc(path))
            log.info("Link: %s", link)
            return link
        else:
            return fmt_loc(path)

    def command_link(self, command_str: str) -> Text:
        return Text.assemble(
            "`", osc8_link(self.explain_url(command_str), command_str), "`", style=COLOR_LINK
        )

    def __str__(self):
        return f"LocalWsUrlFormatter(ws_name={self.ws_name})"


@contextmanager
def ws_formatter(ws_name: Optional[str]):
    """
    Context manager to make it easy to format store paths with links to the local
    server for more info. If ws_name is None, use the default fmt_loc formatter.
    """
    fmt = LocalWsUrlFormatter(ws_name) if ws_name else NoLinkFormatter()
    log.info("Using %s", fmt)
    try:
        yield fmt
    finally:
        pass
