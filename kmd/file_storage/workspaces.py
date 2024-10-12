import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Type, TypeVar

from cachetools import cached

from kmd.config.logger import get_logger, reset_logging
from kmd.config.settings import CONTENT_CACHE_NAME, MEDIA_CACHE_NAME
from kmd.errors import InvalidInput, InvalidState
from kmd.file_storage.file_store import FileStore
from kmd.file_storage.metadata_dirs import CACHE_DIR, METADATA_FILE
from kmd.media.media_tools import reset_media_cache_dir
from kmd.model.canon_url import canonicalize_url
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType
from kmd.model.params_model import ParamValues, USER_SETTABLE_PARAMS
from kmd.model.paths_model import InputArg, StorePath
from kmd.util.format_utils import fmt_path
from kmd.util.url import is_url, Url
from kmd.web_content.file_cache_tools import reset_content_cache_dir

log = get_logger(__name__)


# Suffix used to identify knowledge base directories.
KB_SUFFIX = ".kb"


def check_strict_workspace_name(ws_name: str):
    if not re.match(r"^[\w-]+$", ws_name):
        raise InvalidInput(
            f"Use an alphanumeric name (no spaces or special characters) for the workspace name: `{ws_name}`"
        )


def is_workspace_dir(path: Path) -> bool:
    return (path.is_dir() and str(path).endswith(KB_SUFFIX)) or (path / METADATA_FILE).is_file()


def resolve_workspace_name(name: str | Path) -> Tuple[str, Path]:
    """
    Parse and resolve the given workspace path or name and return a tuple containing
    the workspace name and directory path.

    "example" -> "example", Path("example.kb")  [if example does not exist]
    "example" -> "example", Path("example")  [if example already exists]
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


def find_workspace_dir(path: Path = Path(".")) -> Optional[Path]:
    """
    Get the current workspace directory.
    """
    path = path.absolute()
    while path != Path("/"):
        if is_workspace_dir(path):
            return path
        path = path.parent

    return None


@cached({})
def sandbox_dir() -> Path:
    from kmd.config.settings import SANDBOX_KB_PATH

    kb_path = Path(SANDBOX_KB_PATH).expanduser().resolve()
    if not kb_path.exists():
        os.makedirs(kb_path, exist_ok=True)
    log.info("Sandbox KB path: %s", kb_path)
    return kb_path


def current_workspace_info() -> Tuple[Optional[Path], bool]:
    """
    Get the name of the current workspace (name.kb) or sandbox, or None if not in a workspace
    and sandbox is not being used.
    """
    from kmd.config.settings import global_settings

    dir = find_workspace_dir()
    is_sandbox = False
    if global_settings().use_sandbox:
        is_sandbox = not dir
        if is_sandbox:
            dir = sandbox_dir()
    return dir, is_sandbox


# Cache the file store per directory, since it takes a little while to load.
@cached({})
def _get_file_store(base_dir: Path, is_sandbox: bool) -> FileStore:
    return FileStore(base_dir, is_sandbox)


_last_workspace_dir = None


def current_workspace(log_on_change: bool = True) -> FileStore:
    """
    Get the current workspace. Also updates logging and cache directories to be within that
    workspace, if it has changed.
    """
    workspace_dir, is_sandbox = current_workspace_info()
    if not workspace_dir:
        raise InvalidState(
            f"No workspace found in `{fmt_path(Path('.').absolute())}`.\n"
            "Create one with the `workspace` command."
        )

    reset_logging(workspace_dir)
    reset_media_cache_dir(workspace_dir / CACHE_DIR / MEDIA_CACHE_NAME)
    reset_content_cache_dir(workspace_dir / CACHE_DIR / CONTENT_CACHE_NAME)
    ws = _get_file_store(workspace_dir, is_sandbox)

    global _last_workspace_dir
    if log_on_change and _last_workspace_dir != workspace_dir:
        ws.log_store_info()
        _last_workspace_dir = workspace_dir

    return ws


def current_tmp_dir() -> Path:
    try:
        return current_workspace().dirs.tmp_dir
    except InvalidState:
        return Path(tempfile.gettempdir())


def import_and_load(locator: InputArg) -> Item:
    """
    Ensure that the URL or Item is saved to the workspace.
    """

    if isinstance(locator, str) and is_url(locator):
        item = import_url_to_workspace(Url(locator))
    else:
        ws = current_workspace()
        if isinstance(locator, StorePath):
            # It's already a StorePath.
            item = ws.load(locator)
        else:
            path = Path(locator)
            if not path.exists():
                raise InvalidInput(f"File not found: {path}")

            store_path = ws.add_resource(path)
            item = ws.load(store_path)

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


T = TypeVar("T")


def get_param_value(param_name: str, type: Type[T] = str) -> Optional[T]:
    """
    Get a global parameter value, checking if it is set in the current workspace first.
    """
    try:
        params = current_workspace().get_param_values()
    except InvalidState:
        params = ParamValues({})

    return params.get(param_name, type=type, defaults_info=USER_SETTABLE_PARAMS)
