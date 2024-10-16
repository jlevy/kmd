import os
from os.path import abspath, relpath
from pathlib import Path
from typing import Generator, List, Tuple

from kmd.config.logger import get_logger
from kmd.errors import FileNotFound
from kmd.model.file_formats_model import is_ignored
from kmd.util.format_utils import fmt_path


log = get_logger(__name__)


def walk_by_folder(
    start_path: Path, relative_to: Path, show_hidden: bool = False, recursive: bool = True
) -> Generator[Tuple[str, List[str]], None, None]:
    """
    Simple wrapper around `os.walk`. Yields all files in each folder as
    `(rel_dirname, filenames)` for each directory within `start_path`, where
    `rel_dirname` is relative to `relative_to`. Handles sorting by name
    and skipping hidden files.
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
        rel_dirname = relpath(start_path.parent, relative_to) if relative_to else start_path.parent
        yield rel_dirname, [start_path.name]
        return

    # Walk the directory.
    for dirname, dirnames, filenames in os.walk(start_path):
        # If not recursive, prevent os.walk from descending into subdirectories.
        if not recursive:
            dirnames[:] = []

        dirnames.sort()
        filenames.sort()

        # Filter out ignored directories.
        if not show_hidden:
            dirnames[:] = [d for d in dirnames if not is_ignored(d)]

        # Filter out ignored files.
        filtered_filenames = filenames
        if not show_hidden:
            filtered_filenames = [f for f in filenames if not is_ignored(f)]

        if filtered_filenames:
            rel_dirname = relpath(abspath(dirname), relative_to) if relative_to else dirname
            yield rel_dirname, filtered_filenames
