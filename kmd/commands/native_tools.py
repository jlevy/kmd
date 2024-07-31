"""
Platform-specific tools and utilities.
"""

import os
from pathlib import Path
import shutil
import subprocess
from typing import Tuple
import mimetypes
import webbrowser
from cachetools import cached
from xonsh.platform import ON_WINDOWS, ON_DARWIN, ON_LINUX
from kmd.config.logger import get_logger
from kmd.file_storage.filenames import ext_is_text, parse_filename
from kmd.text_ui.command_output import output
from kmd.config.text_styles import COLOR_ERROR, COLOR_HINT
from kmd.util.url import is_url

log = get_logger(__name__)


def file_info(
    filename: str | Path, max_lines: int = 100, max_bytes: int = 50 * 1024
) -> Tuple[str, int, int]:
    """
    Best effort to guess file type, size, and lines by reading just first part of the file.
    """
    filename = str(filename)
    mime_type, _ = mimetypes.guess_type(filename)
    file_size = os.path.getsize(filename)
    num_lines = 0
    with open(filename, "rb") as f:
        for i, _line in enumerate(f):
            if i >= max_lines or f.tell() > max_bytes:
                break
            num_lines += 1
    return mime_type or "unknown", file_size, num_lines


def native_open(filename: str | Path):
    filename = str(filename)
    log.message("Opening file: %s", filename)
    if ON_DARWIN:
        subprocess.run(["open", filename])
    elif ON_LINUX:
        subprocess.run(["xdg-open", filename])
    elif ON_WINDOWS:
        subprocess.run(["start", filename], shell=True)
    else:
        raise NotImplementedError("Unsupported platform")


@cached({})
def _terminal_supports_sixel() -> bool:
    # This can't be determined easily, so we check for some common terminals.
    term = os.environ.get("TERM", "")
    supported_terms = ["xterm", "xterm-256color", "screen.xterm-256color", "kitty", "iTerm.app"]

    return any(supported_term in term for supported_term in supported_terms)


@cached({})
def _terminal_is_kitty():
    return os.environ.get("TERM") == "xterm-kitty"


@cached({})
def _terminal_supports_osc8() -> bool:
    """
    Attempt to detect if the terminal supports OSC 8 hyperlinks.
    """
    term_program = os.environ.get("TERM_PROGRAM", "")
    term = os.environ.get("TERM", "")

    if term_program in ["iTerm.app", "WezTerm", "Hyper"]:
        return True
    if "kitty" in term or "xterm" in term:
        return True
    if "vscode" in term_program.lower():
        return True

    return False


def _terminal_show_image_sixel(image_path: str | Path, width: int = 800, height: int = 480) -> None:
    if shutil.which("magick") is None:
        raise EnvironmentError("ImageMagick `magick` not found in path; check it is installed?")
    if not _terminal_supports_sixel():
        raise EnvironmentError("Terminal does not support Sixel graphics ({os.environ.get('TERM'})")

    try:
        cmd = ["magick", str(image_path), "-geometry", f"{width}x{height}", "sixel:-"]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise EnvironmentError(f"Failed to display image: {e}")


def _terminal_show_image_kitty(filename: str | Path):
    filename = str(filename)
    try:
        subprocess.run(["kitty", "+kitten", "icat", filename])
    except subprocess.CalledProcessError as e:
        raise EnvironmentError(f"Failed to display image with kitty: {e}")


def terminal_show_image(filename: str | Path):
    """
    Try to display an image in the terminal, using kitty or sixel.
    """
    if _terminal_is_kitty():
        _terminal_show_image_kitty(filename)
    elif _terminal_supports_sixel():
        _terminal_show_image_sixel(filename)
    else:
        raise EnvironmentError("Image display in terminal not supported")


def terminal_show_image_graceful(filename: str | Path):
    try:
        terminal_show_image(filename)
    except EnvironmentError:
        output("[Image: {filename}]", color=COLOR_HINT)


def terminal_link(url: str, text: str, id: str = "") -> str:
    """
    Generate clickable text for terminal emulators supporting OSC 8.
    Id is optional.
    """
    if _terminal_supports_osc8():
        escape_start = f"\x1b]8;id={id};" if id else "\x1b]8;;"  # OSC 8 ; id=ID ; or OSC 8 ; ;
        escape_end = "\x1b]8;;\x1b\\"  # OSC 8 ; ; \

        # Construct the clickable text
        clickable_text = f"{escape_start}{url}{escape_end}{text}{escape_end}"
        return clickable_text
    else:
        return text


def show_file_platform_specific(file_or_url: str | Path):
    file_or_url = str(file_or_url)
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
        elif mime_type and mime_type.startswith("image"):
            try:
                terminal_show_image(file)
            except EnvironmentError:
                native_open(file)
        else:
            native_open(file)
    elif os.path.isdir(file_or_url):
        native_open(file_or_url)
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
        output(f"Error displaying file: {e}", color=COLOR_ERROR)
