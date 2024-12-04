from functools import cache
from pathlib import Path
from typing import Optional, Tuple, Type, TypeVar

from kmd.config.logger import get_logger, reset_logging
from kmd.config.settings import resolve_and_create_dirs, SANDBOX_KB_PATH, SANDBOX_NAME
from kmd.config.setup import print_api_key_setup
from kmd.errors import InvalidInput, InvalidState
from kmd.file_storage.file_store import FileStore
from kmd.file_storage.metadata_dirs import MetadataDirs
from kmd.file_tools.ignore_files import IgnoreFilter, is_ignored_default
from kmd.media.media_tools import reset_media_cache_dir
from kmd.model.args_model import fmt_loc
from kmd.model.params_model import ParamValues, USER_SETTABLE_PARAMS
from kmd.web_content.file_cache_tools import reset_content_cache_dir
from kmd.workspaces.workspace_names import check_strict_workspace_name
from kmd.workspaces.workspace_registry import get_workspace_registry

log = get_logger(__name__)


# Suffix used to identify knowledge base directories.
KB_SUFFIX = ".kb"


def workspace_name(path_or_name: str | Path) -> str:
    """
    Get the workspace name from a path or name.
    """
    path_or_name = str(path_or_name).strip().rstrip("/")
    if not path_or_name:
        raise InvalidInput("Workspace name is required.")

    path = Path(path_or_name)
    name = path.name.rstrip("/").removesuffix(KB_SUFFIX)
    return name


def is_workspace_dir(path: Path) -> bool:
    dirs = MetadataDirs(path)
    return (path.is_dir() and str(path).endswith(KB_SUFFIX)) or dirs.is_initialized()


def enclosing_workspace_dir(path: Path = Path(".")) -> Optional[Path]:
    """
    Get the workspace directory enclosing the given path (itself or a parent or None).
    """
    path = path.absolute()
    while path != Path("/"):
        if is_workspace_dir(path):
            return path
        path = path.parent

    return None


def resolve_workspace(name: str | Path) -> Tuple[str, Path, bool]:
    """
    Parse and resolve the given workspace path or name and return a tuple containing
    the workspace name and a resolved directory path.

    "example" -> "example", Path("example.kb")  [if example does not exist]
    "example" -> "example", Path("example")  [if example already exists]
    "example.kb" -> "example", Path("example.kb")
    "/path/to/example" -> "example", Path("/path/to/example.kb")
    "." -> "current_dir", Path("/path/to/current_dir")
    """
    if not name:
        raise InvalidInput("Workspace name is required.")

    name = str(name).strip().rstrip("/")

    # Check if name is a full path. Otherwise, we'll resolve it relative to the
    # current directory.
    if "/" in name or name.startswith("."):
        resolved = Path(name).resolve()
        parent_dir = resolved.parent
        name = resolved.name
    else:
        parent_dir = Path(".").resolve()

    if (parent_dir / name).exists():
        ws_name = workspace_name(name)
        ws_path = parent_dir / name
    else:
        ws_name = workspace_name(name)
        # By default we add the .kb suffix to the workspace name for clarity for new workspaces.
        ws_path = parent_dir / f"{ws_name}{KB_SUFFIX}"

    is_sandbox = ws_name.lower() == SANDBOX_NAME

    return ws_name, ws_path, is_sandbox


def get_workspace(name: str | Path) -> FileStore:
    """
    Get a workspace by name or path and register the FileStore so we reuse it.
    """
    ws_name, ws_path, is_sandbox = resolve_workspace(check_strict_workspace_name(str(name)))
    ws = get_workspace_registry().load(ws_name, ws_path, is_sandbox)
    return ws


@cache
def sandbox_dir() -> Path:
    kb_path = resolve_and_create_dirs(SANDBOX_KB_PATH, is_dir=True)
    log.info("Sandbox KB path: %s", kb_path)
    return kb_path


def get_sandbox_workspace() -> FileStore:
    """
    Get the sandbox workspace.
    """
    return get_workspace_registry().load(SANDBOX_NAME, sandbox_dir(), True)


def _infer_workspace_info() -> Tuple[Optional[Path], bool]:
    from kmd.config.settings import global_settings

    dir = enclosing_workspace_dir()
    is_sandbox = False
    if global_settings().use_sandbox:
        is_sandbox = not dir
        if is_sandbox:
            dir = sandbox_dir()
    return dir, is_sandbox


def _switch_current_workspace(base_dir: Path) -> FileStore:
    """
    Switch the current workspace to the given directory.
    Updates logging and cache directories to be within that workspace.
    Does not reload the workspace if it's already loaded.
    """
    ws_name, ws_path, is_sandbox = resolve_workspace(base_dir)
    ws_dirs = MetadataDirs(ws_path)

    reset_logging(ws_dirs.base_dir)
    reset_media_cache_dir(ws_dirs.media_cache_dir)
    reset_content_cache_dir(ws_dirs.content_cache_dir)

    return get_workspace_registry().load(ws_name, ws_path, is_sandbox)


def current_workspace(silent: bool = False) -> FileStore:
    """
    Get the current workspace based on the current working directory.
    Also updates logging and cache directories if this has changed.
    """

    base_dir, is_sandbox = _infer_workspace_info()
    if not base_dir:
        raise InvalidState(
            f"No workspace found in {fmt_loc(Path('.').absolute())}.\n"
            "Create one with the `workspace` command."
        )

    ws = _switch_current_workspace(base_dir)

    if not silent:
        # Delayed, once-only logging of any setup warnings.
        print_api_key_setup(once=True)
        ws.log_store_info(once=True)

    return ws


def current_ignore() -> IgnoreFilter:
    """
    Get the current ignore filter.
    """
    try:
        return current_workspace().is_ignored
    except InvalidState:
        return is_ignored_default


T = TypeVar("T")


def workspace_param_value(param_name: str, type: Type[T] = str) -> Optional[T]:
    """
    Get a global parameter value, checking if it is set in the current workspace first.
    """
    try:
        params = current_workspace().params.get_values()
    except InvalidState:
        params = ParamValues()

    return params.get(param_name, type=type, defaults_info=USER_SETTABLE_PARAMS)
