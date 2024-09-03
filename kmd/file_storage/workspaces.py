from pathlib import Path
import re
import tempfile
from typing import Optional, Tuple
from cachetools import cached
from kmd.media.media_download import reset_media_cache_dir
from kmd.media.web import reset_web_cache_dir
from kmd.model.canon_url import canonicalize_url
from kmd.model.errors_model import InvalidInput, InvalidState
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType
from kmd.file_storage.file_store import CACHE_DIR, FileStore
from kmd.model.locators import Locator, StorePath
from kmd.model.params_model import USER_SETTABLE_PARAMS, param_lookup
from kmd.util.url import Url, is_url
from kmd.config.logger import get_logger, reset_log_root

log = get_logger(__name__)


# Suffix used to identify knowledge base directories.
KB_SUFFIX = ".kb"


def check_strict_workspace_name(ws_name: str):
    if not re.match(r"^[\w-]+$", ws_name):
        raise InvalidInput(
            f"Use an alphanumeric name (no spaces or special characters) for the workspace name: `{ws_name}`"
        )


def resolve_workspace_name(name: str | Path) -> Tuple[str, Path]:
    """
    Parse and resolve the given workspace path or name and return a tuple containing
    the workspace name and directory path.

    "example" -> "example", Path("example.kb")
    "example.kb" -> "example", Path("example.kb")
    "/path/to/example" -> "example", Path("/path/to/example.kb")
    "." -> "current_dir", Path("/path/to/current_dir")
    """
    if not name:
        raise InvalidInput("Workspace name is required.")

    name = str(name).strip().rstrip("/")

    if "/" in name or name.startswith("."):
        resolved = Path(name).resolve()
        parent_dir = resolved.parent
        name = resolved.name
    else:
        parent_dir = Path(".").resolve()

    if (parent_dir / name).exists():
        ws_name = name
        ws_path = parent_dir / name
    else:
        ws_name = name.removesuffix(KB_SUFFIX)
        name_with_suffix = name if name.endswith(KB_SUFFIX) else f"{name}{KB_SUFFIX}"
        ws_path = parent_dir / name_with_suffix

    return ws_name, ws_path


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

    raise InvalidState(
        f"No workspace found in `{cwd}`.\nA workspace directory should end in .kb; create one with the `workspace` command."
    )


def current_workspace_name() -> Optional[str]:
    """
    Get the name of the current workspace (name.kb) or None if not in a .kb directory.
    """
    workspace_name = None
    try:
        workspace_name = current_workspace_dir().name
    except InvalidState:
        pass
    return workspace_name


# Cache the file store per directory, since it takes a little while to load.
@cached({})
def _get_file_store(base_dir: Path) -> FileStore:
    return FileStore(base_dir)


_last_workspace_dir = None


def current_workspace() -> FileStore:
    """
    Get the current workspace. Also updates logging and cache directories to be
    within that workspace, if it has changed.
    """
    workspace_dir = current_workspace_dir()
    reset_log_root(workspace_dir)
    reset_media_cache_dir(workspace_dir / CACHE_DIR / "media")
    reset_web_cache_dir(workspace_dir / CACHE_DIR / "web")
    ws = _get_file_store(workspace_dir)

    global _last_workspace_dir
    if _last_workspace_dir != workspace_dir:
        ws.log_store_info()
        _last_workspace_dir = workspace_dir

    return ws


def current_workspace_tmp_dir() -> Path:
    try:
        return current_workspace().tmp_dir
    except InvalidState:
        return Path(tempfile.gettempdir())


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


def get_param_value(param_name: str) -> Optional[str]:
    """
    Get a global parameter value, checking if it is set in the current workspace first.
    """
    try:
        params = current_workspace().get_params()
    except InvalidState:
        params = {}

    return param_lookup(params, param_name, USER_SETTABLE_PARAMS)
