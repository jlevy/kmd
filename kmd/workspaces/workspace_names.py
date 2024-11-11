import re
from pathlib import Path

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput

log = get_logger(__name__)


# Suffix used to identify knowledge base directories.
KB_SUFFIX = ".kb"


def check_strict_workspace_name(ws_name: str) -> str:
    ws_name = str(ws_name).strip().rstrip("/")
    if not re.match(r"^[\w-]+$", ws_name):
        raise InvalidInput(
            f"Use an alphanumeric name (no spaces or special characters) for the workspace name: `{ws_name}`"
        )
    return ws_name


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
