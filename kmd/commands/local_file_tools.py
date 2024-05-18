"""
Platform-specific file handling utilities.
"""

import os
import subprocess
import sys
from typing import Tuple
import mimetypes
import webbrowser
from xonsh.platform import ON_WINDOWS, ON_DARWIN, ON_LINUX
from kmd.file_storage.filenames import parse_filename
from kmd.model.items_model import FileExt

from kmd.util.url_utils import is_url


def file_info(
    file_path: str, max_lines: int = 100, max_bytes: int = 50 * 1024
) -> Tuple[str, int, int]:
    """
    Get file type, size, and lines by reading just first part of the file.
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    file_size = os.path.getsize(file_path)
    num_lines = 0
    with open(file_path, "rb") as f:
        for i, _line in enumerate(f):
            if i >= max_lines or f.tell() > max_bytes:
                break
            num_lines += 1
    return mime_type or "unknown", file_size, num_lines


def _native_open(filename: str):
    if ON_DARWIN:
        subprocess.run(["open", filename])
    elif ON_LINUX:
        subprocess.run(["xdg-open", filename])
    elif ON_WINDOWS:
        subprocess.run(["start", filename], shell=True)
    else:
        raise NotImplementedError("Unsupported platform")


def open_platform_specific(file_or_url: str):
    if is_url(file_or_url) or file_or_url.endswith(".html"):
        webbrowser.open(file_or_url)
    elif os.path.isfile(file_or_url):
        file = file_or_url
        mime_type, file_size, num_lines = file_info(file)
        _dirname, _name, _item_type, ext = parse_filename(file)
        if FileExt(ext).is_text() or mime_type and mime_type.startswith("text"):
            view_file(file, use_less=num_lines > 40 or file_size > 20 * 1024)
        else:
            _native_open(file)
    elif os.path.isdir(file_or_url):
        # TODO: Consider making this a list of files.
        _native_open(file_or_url)
    else:
        raise ValueError("File does not exist")


def view_file(file_path: str, use_less: bool = True):
    """
    Displays a file in the console with pagination and syntax highlighting.
    """
    # TODO: Update this to handle YAML frontmatter more nicely.
    try:
        if use_less:
            subprocess.run(f"pygmentize -g {file_path} | less -R", shell=True, check=True)
        else:
            subprocess.run(f"pygmentize -g {file_path}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error displaying file: {e}", file=sys.stderr)
