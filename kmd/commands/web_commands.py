import urllib.parse

from kmd.commands.command_registry import kmd_command
from kmd.shell_tools.native_tools import native_open_url


@kmd_command
def browser(url_or_query: str) -> None:
    """
    Open a URL or query in the browser.
    """
    native_open_url(url_or_query)


@kmd_command
def search_google(query: str) -> None:
    """
    Search Google for a query.
    """
    native_open_url(f"https://www.google.com/search?q={urllib.parse.quote(query)}")


@kmd_command
def search_youtube(query: str) -> None:
    """
    Search YouTube for a query.
    """
    params = {"search_query": query}
    url = f"https://www.youtube.com/results?{urllib.parse.urlencode(params)}"
    native_open_url(url)
