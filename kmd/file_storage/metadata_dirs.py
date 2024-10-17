"""
Layout of the metadata files and directories with the file store.
"""

import os
from pathlib import Path

from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.config.settings import DOT_DIR
from kmd.file_storage.persisted_yaml import PersistedYaml
from kmd.util.format_utils import fmt_path

log = get_logger(__name__)


ARCHIVE_DIR = f"{DOT_DIR}/archive"
SETTINGS_DIR = f"{DOT_DIR}/settings"

CACHE_DIR = f"{DOT_DIR}/cache"
INDEX_DIR = f"{DOT_DIR}/index"
HISTORY_DIR = f"{DOT_DIR}/history"
TMP_DIR = f"{DOT_DIR}/tmp"
METADATA_FILE = f"{DOT_DIR}/metadata.yml"
HISTORY_FILE = "shell_history.yml"

# Store format versioning, to allow warnings or checks as this format evolves.
# sv1: Initial version.
STORE_VERSION = "sv1"


@dataclass
class MetadataDirs:
    archive_dir: Path
    settings_dir: Path
    cache_dir: Path
    index_dir: Path
    history_dir: Path
    tmp_dir: Path

    @property
    def shell_history(self) -> Path:
        return self.history_dir / HISTORY_FILE


def initialize_store_dirs(base_dir: Path):
    # Initialize metadata file.
    metadata_file = base_dir / METADATA_FILE
    metadata = PersistedYaml(metadata_file, init_value={"store_version": STORE_VERSION})

    if metadata.read().get("store_version") != STORE_VERSION:
        log.warning(
            "Store metadata is version %r but we are using version %r: %s",
            metadata.read().get("store_version"),
            STORE_VERSION,
            fmt_path(metadata_file),
        )

    # Directories directly used by the FileStore.
    archive_dir = base_dir / ARCHIVE_DIR
    os.makedirs(archive_dir, exist_ok=True)
    settings_dir = base_dir / SETTINGS_DIR
    os.makedirs(settings_dir, exist_ok=True)

    # Directories not used for file storage directly but co-located in the workspace.
    cache_dir = base_dir / CACHE_DIR
    os.makedirs(cache_dir, exist_ok=True)
    index_dir = base_dir / INDEX_DIR
    os.makedirs(index_dir, exist_ok=True)
    history_dir = base_dir / HISTORY_DIR
    os.makedirs(history_dir, exist_ok=True)
    tmp_dir = base_dir / TMP_DIR
    os.makedirs(tmp_dir, exist_ok=True)

    return MetadataDirs(
        archive_dir=archive_dir,
        settings_dir=settings_dir,
        cache_dir=cache_dir,
        index_dir=index_dir,
        history_dir=history_dir,
        tmp_dir=tmp_dir,
    )
