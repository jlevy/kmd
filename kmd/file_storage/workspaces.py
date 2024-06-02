from pathlib import Path
from typing import Optional, Tuple
from pathlib import Path
from typing import Tuple
from cachetools import cached
from kmd.model.canon_url import canonicalize_url
from kmd.model.items_model import Format, Item, ItemType
from kmd.file_storage.file_store import FileStore
from kmd.model.locators import Locator, StorePath
from kmd.model.items_model import Item
from kmd.util.url import Url, is_url
from kmd.config.logger import get_logger

log = get_logger(__name__)


# Suffix used to identify knowledge base directories.
KB_SUFFIX = ".kb"


def canon_workspace_name(name: str) -> Tuple[str, str]:
    name = name.strip("/ ")
    workspace_name = name.removesuffix(KB_SUFFIX)
    workspace_dir = name if name.endswith(KB_SUFFIX) else f"{name}{KB_SUFFIX}"
    return workspace_name, workspace_dir


def current_workspace_dir() -> Path:
    """
    Get the current workspace directory.
    """
    cwd = Path(".").absolute()
    path = cwd
    while path != Path("/"):
        if str(path).endswith(KB_SUFFIX):
            return path
        path = path.parent

    raise ValueError(
        f"No workspace found in `{cwd}`. A workspace directory should end in .kb; create one with the `workspace` command)"
    )


def current_workspace_name() -> Optional[str]:
    """
    Get the name of the current workspace (name.kb) or None if not in a .kb directory.
    """
    workspace_name = None
    try:
        workspace_name = current_workspace_dir().name
    except ValueError:
        pass
    return workspace_name


# Cache the file store per directory, since it takes a little while to load.
@cached({})
def _new_workspace_dir(base_dir: Path) -> FileStore:
    return FileStore(base_dir)


def current_workspace() -> FileStore:
    """
    Get the current workspace.
    """
    return _new_workspace_dir(current_workspace_dir())


def show_workspace_info() -> None:
    workspace = current_workspace()
    workspace.log_store_info()


def ensure_saved(locator: Locator) -> Item:
    """
    Ensure that the URL or Item is saved to the workspace.
    """

    if is_url(locator):
        item = import_url_to_workspace(Url(locator))
    else:
        workspace = current_workspace()
        item = workspace.load(StorePath(locator))

    return item


def import_url_to_workspace(url: Url) -> Item:
    """
    Import a URL as a resource. Should call fetch_page to fill in metadata.
    """
    canon_url = canonicalize_url(url)
    log.message(
        "Importing url: %s%s", canon_url, f" canonicalized from {url}" if url != canon_url else ""
    )
    item = Item(ItemType.resource, url=canon_url, format=Format.url)
    workspace = current_workspace()
    workspace.save(item)
    return item
