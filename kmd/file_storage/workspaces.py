import logging
from pathlib import Path
from os.path import basename
from typing import Tuple
import logging
from pathlib import Path
from typing import Tuple
from os import path

from kmd.file_storage.file_store import FileStore
from kmd.model.url import canonicalize_url
from kmd.model.locators import Locator, StorePath
from kmd.model.items_model import Format, Item, ItemType
from kmd.util.url_utils import Url, is_url

log = logging.getLogger(__name__)

WS_SUFFIX = ".ws"


def canon_workspace_name(name: str) -> Tuple[str, str]:
    name = name.strip()
    workspace_name = name.removesuffix(WS_SUFFIX)
    workspace_dir = name if name.endswith(WS_SUFFIX) else f"{name}{WS_SUFFIX}"
    return workspace_name, workspace_dir


def validate_workspace_dir(base_dir: Path | str) -> None:
    if not str(base_dir).endswith(WS_SUFFIX):
        raise ValueError(
            f"Directory `{base_dir}` is not a workspace (should end in .ws; create one with the `workspace` command)"
        )


def current_workspace_dir() -> Path:
    """
    Get the current workspace directory.
    """
    cwd = Path(".").absolute()
    parent_dir = basename(cwd)
    validate_workspace_dir(parent_dir)
    return cwd


def current_workspace() -> FileStore:
    """
    Get the current workspace.
    """
    return FileStore(current_workspace_dir())


def show_workspace_info() -> None:
    workspace = current_workspace()
    log.warning(
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
        log.warning("Saved url: %s", store_path)
    else:
        item = workspace.load(StorePath(locator))

    return item
