import threading
from pathlib import Path
from typing import Dict, Optional

from cachetools import cached
from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.file_storage.file_store import FileStore
from kmd.util.format_utils import fmt_path

log = get_logger(__name__)


# Cache the file store per directory, since it takes a little while to load.
@cached({})
def load_file_store(base_dir: Path, is_sandbox: bool) -> FileStore:
    file_store = FileStore(base_dir, is_sandbox)
    return file_store


@dataclass(frozen=True)
class WorkspaceInfo:
    name: str
    path: Path
    is_sandbox: bool


class WorkspaceRegistry:
    def __init__(self):
        self._workspaces: Dict[str, WorkspaceInfo] = {}
        self._lock = threading.RLock()

    def load(self, name: str, path: Path, is_sandbox: bool) -> FileStore:
        with self._lock:
            info = self._workspaces.get(name)

            if not info:
                info = WorkspaceInfo(name, path.resolve(), is_sandbox)
                self._workspaces[name] = info
                log.info("Registered workspace: %s -> %s", name, fmt_path(path))

            return load_file_store(info.path, info.is_sandbox)

    def get(self, name: str) -> Optional[WorkspaceInfo]:
        with self._lock:
            return self._workspaces.get(name)

    def get_by_path(self, path: Path) -> Optional[WorkspaceInfo]:
        path = path.resolve()
        with self._lock:
            for info in self._workspaces.values():
                if info.path == path:
                    return info
            return None


# Global registry instance.
_registry = WorkspaceRegistry()


def get_workspace_registry() -> WorkspaceRegistry:
    return _registry
