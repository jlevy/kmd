from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from rich.text import Text

from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_HINT
from kmd.errors import InvalidState
from kmd.model.args_model import fmt_loc

from kmd.model.paths_model import StorePath
from kmd.shell.kyrm_codes import Kri, KriLink, TextTooltip
from kmd.util.atomic import AtomicVar
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


class LinkFormatter(ABC):
    """
    Base class for adding URL links to values.
    """

    @abstractmethod
    def tooltip_link(self, text: str, tooltip: Optional[str] = None) -> Text:
        """Text with a tooltip."""
        pass

    @abstractmethod
    def path_link(self, path: Path, link_text: str) -> Text:
        """A link to a local path (file or directory)."""
        pass

    @abstractmethod
    def command_link(self, command_str: str) -> Text:
        """Text that links to a command."""
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

    def __str__(self):
        return "PlaintextFormatter()"


class DefaultLinkFormatter(PlaintextFormatter):
    """
    A formatter that adds OSC 8 links to the local server.
    """

    def tooltip_link(self, text: str, tooltip: Optional[str] = None) -> Text:
        if tooltip:
            return KriLink.with_attrs(text, hover=TextTooltip(text=tooltip)).as_rich()
        else:
            return Text(text)

    def path_link(self, path: Path, link_text: str) -> Text:
        from kmd.server.local_server_routes import local_url

        url = local_url.view_file(path)
        return KriLink.with_attrs(link_text, href=url).as_rich()

    def command_link(self, command_str: str) -> Text:
        from kmd.server.local_server_routes import local_url

        url = local_url.explain(text=command_str)
        return Text.assemble(
            Text("`", style=COLOR_HINT),
            KriLink.with_attrs(command_str, href=url).as_rich(),
            Text("`", style=COLOR_HINT),
        )

    def __str__(self):
        return "DefaultFormatter()"


class WorkspaceLinkFormatter(DefaultLinkFormatter):
    """
    A formatter that also has workspace context so can add workspace-specific links.
    Works fine for non-workspace Paths too.
    """

    def __init__(self, ws_name: str):
        self.ws_name = ws_name

    def path_link(self, path: Path, link_text: str) -> Text:
        if isinstance(path, StorePath):
            from kmd.server.local_server_routes import local_url

            url = local_url.view_item(store_path=path, ws_name=self.ws_name)
            return KriLink(kri=Kri.for_url(url), link_text=link_text).as_rich()
        else:
            return super().path_link(path, link_text)

    def __str__(self):
        return f"WorkspaceLinkFormatter(ws_name={self.ws_name})"


_local_urls_enabled = AtomicVar(False)


def enable_local_urls(enabled: bool):
    _local_urls_enabled.set(enabled)


@contextmanager
def local_url_formatter(ws_name: Optional[str] = None):
    """
    Context manager to make it easy to format store paths with links to the local
    server for more info. If ws_name is None, use the default formatter.
    """
    if _local_urls_enabled:
        try:
            ws_name = current_workspace().name
            fmt = WorkspaceLinkFormatter(ws_name)
        except InvalidState:
            fmt = DefaultLinkFormatter()
    else:
        fmt = PlaintextFormatter()

    log.info("Using %s", fmt)
    try:
        yield fmt
    finally:
        pass