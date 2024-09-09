import os
from pathlib import Path
from os.path import relpath, abspath
from typing import Generator, List, Tuple
from kmd.config.logger import get_logger
from kmd.model.errors_model import FileNotFound
from kmd.model.file_formats_model import (
    is_ignored,
)
from kmd.text_formatting.text_formatting import fmt_path

# TODO: Options to cap number of files returned per folder and number of folders walked.
# TODO: Support other sorting options.

log = get_logger(__name__)


def walk_by_folder(
    start_path: Path, relative_to: Path, show_hidden: bool = False
) -> Generator[Tuple[str, List[str]], None, None]:
    """
    Yields all files in each folder as `(rel_dirname, filenames)` for each directory in
    the store, where `rel_dirname` is relative to `base_dir`. Handles sorting and skipping
    hidden files.
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
