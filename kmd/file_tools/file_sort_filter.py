from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional

import humanfriendly
import pandas as pd
from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.errors import FileNotFound, InvalidInput
from kmd.file_tools.file_walk import IgnoreFilter, walk_by_dir
from kmd.model.paths_model import fmt_loc


log = get_logger(__name__)


class SortOption(str, Enum):
    filename = "filename"
    size = "size"
    accessed = "accessed"
    created = "created"
    modified = "modified"


class GroupByOption(str, Enum):
    flat = "flat"
    parent = "parent"
    suffix = "suffix"


class FileType(str, Enum):
    file = "file"
    dir = "dir"


@dataclass(frozen=True)
class FileInfo:
    path: str
    relative_path: str
    filename: str
    suffix: str
    parent: str
    size: int
    accessed: datetime
    created: datetime
    modified: datetime
    type: FileType


def get_file_info(file_path: Path, base_path: Path) -> FileInfo:
    stat = file_path.stat()
    return FileInfo(
        path=str(file_path.resolve()),
        relative_path=str(file_path.relative_to(base_path)),
        filename=file_path.name,
        suffix=file_path.suffix,
        parent=str(file_path.parent.relative_to(base_path)),
        size=stat.st_size,
        accessed=datetime.fromtimestamp(stat.st_atime, tz=timezone.utc),
        created=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
        modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        type=FileType.dir if file_path.is_dir() else FileType.file,
    )


def parse_since(since: str) -> float:
    try:
        since_seconds = humanfriendly.parse_timespan(since)
        return since_seconds
    except humanfriendly.InvalidTimespan:
        raise InvalidInput(
            f"Invalid 'since' format '{since}'. "
            "Use formats like '5m' (5 minutes), '1d' (1 day), or '2w' (2 weeks)."
        )


@dataclass
class FileListing:
    """
    Results of walking a directory and collecting file information.
    """

    files: List[FileInfo]
    start_paths: List[Path]
    files_total: int
    files_matching: int
    files_ignored: int
    dirs_ignored: int
    size_total: int
    size_matching: int
    since_timestamp: float

    def as_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame([file.__dict__ for file in self.files])
        return df


def collect_files(
    start_paths: List[Path],
    recursive=False,
    ignore: Optional[IgnoreFilter] = None,
    since_seconds: float = 0.0,
    base_path: Optional[Path] = None,
) -> FileListing:
    files_info = []

    for path in start_paths:
        if not path.exists():
            raise FileNotFound(f"Path not found: {fmt_loc(path)}")

    since_timestamp = (
        datetime.now(timezone.utc).timestamp() - since_seconds if since_seconds else 0.0
    )
    if since_timestamp:
        log.info(
            "Collecting files modified in last %s seconds (since %s).",
            since_seconds,
            datetime.fromtimestamp(since_timestamp),
        )

    files_total = 0
    size_total = 0
    size_matching = 0

    if not base_path:
        base_path = Path(".")

    for path in start_paths:

        dirs_ignored = 0
        files_ignored = 0

        log.debug("Walking folder: %s", fmt_loc(path))

        try:
            for flist in walk_by_dir(
                path, relative_to=base_path, ignore=ignore, recursive=recursive
            ):

                log.debug("Walking folder: %s: %s", fmt_loc(flist.parent_dir), flist.filenames)

                files_ignored += flist.files_ignored
                dirs_ignored += flist.dirs_ignored

                dir_path = base_path / flist.parent_dir
                for filename in flist.filenames:
                    info = get_file_info(dir_path / filename, base_path)

                    if not since_timestamp or info.modified.timestamp() > since_timestamp:
                        files_info.append(info)
                        size_matching += info.size

                    files_total += 1
                    size_total += info.size

        except FileNotFound as e:
            log.warning("File unexpectedly missing: %s", e)
            continue

    return FileListing(
        files=files_info,
        start_paths=start_paths,
        files_total=files_total,
        files_matching=len(files_info),
        files_ignored=files_ignored,
        dirs_ignored=dirs_ignored,
        size_total=size_total,
        size_matching=size_matching,
        since_timestamp=since_timestamp,
    )
