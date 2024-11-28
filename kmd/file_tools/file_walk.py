import os
from dataclasses import dataclass
from os.path import abspath, relpath
from pathlib import Path
from typing import Callable, Generator, List, Optional

from kmd.config.logger import get_logger
from kmd.errors import FileNotFound
from kmd.model.args_model import fmt_loc


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
    files_skipped: int
    dirs_skipped: int
    num_files: int  # Total number of files in the directory before capping


IgnoreFilter = Callable[[str | Path], bool]


def walk_by_dir(
    start_path: Path,
    relative_to: Path,
    ignore: Optional[IgnoreFilter] = None,
    max_depth: int = -1,
    max_files_per_subdir: int = -1,
    max_files_total: int = -1,
) -> Generator[FileList, None, None]:
    """
    Simple wrapper around `os.walk`. Yields all files in each folder as a
    `FileList`. Filenames are relative to `parent_dir`, which is relative to
    `relative_to`. Handles sorting by name and skipping ignored files and
    directories based on the `ignore` filter.

    :param max_depth: Maximum depth to recurse into directories. -1 means no limit.
    :param max_files_per_subdir: Maximum number of files to yield per subdirectory.
    :param max_files: Maximum total number of files to yield.
    """

    start_path = start_path.resolve()
    if not start_path.exists():
        raise FileNotFound(f"Start path not found: {fmt_loc(start_path)}")

    if relative_to:
        relative_to = relative_to.resolve()
        if not relative_to.exists():
            raise FileNotFound(f"Directory not found: {fmt_loc(relative_to)}")

    # Special case of a single file.
    if start_path.is_file():
        parent_dir = relpath(start_path.parent, relative_to) if relative_to else start_path.parent
        yield FileList(
            parent_dir,
            [start_path.name],
            files_ignored=0,
            dirs_ignored=0,
            files_skipped=0,
            dirs_skipped=0,
            num_files=1,
        )
        return

    files_so_far = 0
    for dirname, dirnames, filenames in os.walk(start_path):
        current_depth = len(Path(dirname).relative_to(start_path).parts)

        # Handle max_depth.
        if max_depth >= 0 and current_depth >= max_depth:
            dirnames[:] = []

        # Filter out ignored directories.
        if ignore:
            prev_dirs_len = len(dirnames)
            dirnames[:] = [d for d in dirnames if not ignore(d)]
            dirs_ignored = prev_dirs_len - len(dirnames)
        else:
            dirs_ignored = 0

        # Sort directories and files.
        # TODO: Custom sort function so walk can prioritize by other criteria.
        dirnames.sort()
        filenames.sort()

        # Filter out ignored files.
        if ignore:
            prev_files_len = len(filenames)
            filenames = [f for f in filenames if not ignore(f)]
            files_ignored = prev_files_len - len(filenames)
        else:
            files_ignored = 0

        num_files = len(filenames)  # Total files before capping
        num_dirs = len(dirnames)

        # Apply max_files_per_subdir
        if max_files_per_subdir > 0:
            filenames = filenames[:max_files_per_subdir]

        num_files_capped = len(filenames)

        # Apply max_files limit
        if max_files_total > 0:
            files_remaining = max_files_total - files_so_far
            if files_remaining <= 0:
                # Stop traversal
                dirnames[:] = []
                break
            if num_files_capped > files_remaining:
                filenames = filenames[:files_remaining]
                num_files_capped = len(filenames)

        files_so_far += num_files_capped

        if filenames:
            parent_dir = relpath(abspath(dirname), relative_to) if relative_to else dirname
            yield FileList(
                parent_dir,
                filenames,
                files_ignored,
                dirs_ignored,
                files_skipped=num_files - len(filenames),
                dirs_skipped=num_dirs - len(dirnames),
                num_files=num_files,
            )

        # Check if max_files limit is reached after adding files
        if max_files_total > 0 and files_so_far >= max_files_total:
            dirnames[:] = []
            break
