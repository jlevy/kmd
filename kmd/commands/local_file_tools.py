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
from kmd.config.logger import get_logger
from kmd.file_storage.filenames import ext_is_text, parse_filename
from kmd.util.url import is_url

log = get_logger(__name__)


def file_info(
    filename: str, max_lines: int = 100, max_bytes: int = 50 * 1024
) -> Tuple[str, int, int]:
    """
    Get file type, size, and lines by reading just first part of the file.
    """
    mime_type, _ = mimetypes.guess_type(filename)
    file_size = os.path.getsize(filename)
    num_lines = 0
    with open(filename, "rb") as f:
        for i, _line in enumerate(f):
            if i >= max_lines or f.tell() > max_bytes:
                break
            num_lines += 1
    return mime_type or "unknown", file_size, num_lines


def _native_open(filename: str):
    log.message("Opening file: %s", filename)
    if ON_DARWIN:
        subprocess.run(["open", filename])
    elif ON_LINUX:
        subprocess.run(["xdg-open", filename])
    elif ON_WINDOWS:
        subprocess.run(["start", filename], shell=True)
    else:
        raise NotImplementedError("Unsupported platform")


def _in_kitty_terminal():
    return os.environ.get("TERM") == "xterm-kitty"


def kitty_display_image(filename: str):
    subprocess.run(["kitty", "+kitten", "icat", filename])


def open_platform_specific(file_or_url: str):
    if is_url(file_or_url) or file_or_url.endswith(".html"):
        if not is_url(file_or_url):
            file_or_url = f"file://{os.path.abspath(file_or_url)}"
        log.message("Opening URL in browser: %s", file_or_url)
        webbrowser.open(file_or_url)
    elif os.path.isfile(file_or_url):
        file = file_or_url
        mime_type, file_size, num_lines = file_info(file)
        _dirname, _name, _item_type, ext = parse_filename(file)
        if ext_is_text(ext) or mime_type and mime_type.startswith("text"):
            view_file(file, use_less=num_lines > 40 or file_size > 20 * 1024)
        elif _in_kitty_terminal() and mime_type and mime_type.startswith("image"):
            # Support kitty terminal image display, if we are running in kitty.
            kitty_display_image(file)
        else:
            _native_open(file)
    elif os.path.isdir(file_or_url):
        _native_open(file_or_url)
    else:
        raise FileNotFoundError(f"File does not exist: {file_or_url}")


def view_file(filename: str, use_less: bool = True):
    """
    Displays a file in the console with pagination and syntax highlighting.
    """
    # TODO: Update this to handle YAML frontmatter more nicely.
    try:
        if use_less:
            subprocess.run(f"pygmentize -g {filename} | less -R", shell=True, check=True)
        else:
            subprocess.run(f"pygmentize -g {filename}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error displaying file: {e}", file=sys.stderr)
