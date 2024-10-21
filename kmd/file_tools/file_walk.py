import os
from dataclasses import dataclass
from os.path import abspath, relpath
from pathlib import Path
from typing import Callable, Generator, List, Optional

from kmd.config.logger import get_logger
from kmd.errors import FileNotFound
from kmd.util.format_utils import fmt_path


log = get_logger(__name__)


@dataclass(frozen=True)
class FileList:
    """
    A flat list of files in a directory.
    """

    parent_dir: str
    filenames: List[str]
    files_ignored: int
    dirs_ignored: int


IgnoreFilter = Callable[[str | Path], bool]


def walk_by_dir(
    start_path: Path,
    relative_to: Path,
    recursive: bool = True,
    ignore: Optional[IgnoreFilter] = None,
) -> Generator[FileList, None, None]:
    """
    Simple wrapper around `os.walk`. Yields all files in each folder as a
    `FileList`. Filenames are relative to `parent_dir`, which is relative to
    `relative_to`. Handles sorting by name and skipping ignored files and
    directories based on the `ignore` filter.
    """

    start_path = start_path.resolve()
    if not start_path.exists():
        raise FileNotFound(f"Start path not found: {fmt_path(start_path)}")

    if relative_to:
        relative_to = relative_to.resolve()
        if not relative_to.exists():
            raise FileNotFound(f"Directory not found: {fmt_path(relative_to)}")

    # Special case of a single file.
    if start_path.is_file():
        parent_dir = relpath(start_path.parent, relative_to) if relative_to else start_path.parent
        yield FileList(parent_dir, [start_path.name], 0, 0)
        return

    # Walk the directory.
    dirs_ignored = 0
    files_ignored = 0
    for dirname, dirnames, filenames in os.walk(start_path):
        # If not recursive, prevent os.walk from descending into subdirectories.
        if not recursive:
            dirnames[:] = []

        dirnames.sort()
        filenames.sort()

        # Filter out ignored directories.
        if ignore:
            prev_len = len(dirnames)
            dirnames[:] = [d for d in dirnames if not ignore(d)]
            dirs_ignored = prev_len - len(dirnames)

        # Filter out ignored files.
        filtered_filenames = filenames
        if ignore:
            filtered_filenames = [f for f in filenames if not ignore(f)]
            files_ignored = len(filenames) - len(filtered_filenames)

        if filtered_filenames:
            parent_dir = relpath(abspath(dirname), relative_to) if relative_to else dirname
            yield FileList(parent_dir, filtered_filenames, files_ignored, dirs_ignored)
