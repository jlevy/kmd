from pathlib import Path
from typing import Optional, Tuple
import logging
from pathlib import Path
from typing import Tuple
from os import path

from kmd.file_storage.file_store import FileStore
from kmd.model.url import canonicalize_url
from kmd.model.locators import Locator, StorePath
from kmd.model.items_model import Format, Item, ItemType
from kmd.util.url_utils import Url, is_url
from kmd.config.logging import get_logger

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


def current_workspace() -> FileStore:
    """
    Get the current workspace.
    """
    return FileStore(current_workspace_dir())


def show_workspace_info() -> None:
    workspace = current_workspace()
    log.message(
        "Using workspace at %s (%s items)",
        path.abspath(workspace.base_dir),
        len(workspace.uniquifier),
    )
    # TODO: Log more info (optionally in longer form with paging).


def ensure_saved(locator: Locator) -> Item:
    """
    Ensure that the URL or Item is saved to the workspace.
    """

    workspace = current_workspace()

    if is_url(locator):
        url = canonicalize_url(Url(locator))
        item = Item(ItemType.resource, url=url, format=Format.url)
        store_path = workspace.save(item)
        log.message("Saved url: %s", store_path)
    else:
        item = workspace.load(StorePath(locator))

    return item
