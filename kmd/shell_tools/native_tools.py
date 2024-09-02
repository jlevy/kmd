"""
Platform-specific tools and utilities.
"""

from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import shutil
import subprocess
import shlex
from typing import Tuple
import mimetypes
import webbrowser
from cachetools import TTLCache, cached
from xonsh.platform import ON_WINDOWS, ON_DARWIN, ON_LINUX
from kmd.config.logger import get_logger
from kmd.config.settings import get_settings
from kmd.model.file_formats_model import parse_filename
from kmd.model.errors_model import SetupError
from kmd.model.file_formats_model import file_ext_is_text
from kmd.text_ui.command_output import output
from kmd.config.text_styles import BAT_THEME, COLOR_ERROR, COLOR_HINT
from kmd.util.url import is_url

log = get_logger(__name__)


class CmdlineTool(Enum):
    """
    External tools that we like to use.
    """

    less = "less"
    tail = "tail"
    pygmentize = "pygmentize"
    ripgrep = "rg"
    bat = "bat"
    ffmpeg = "ffmpeg"


@dataclass(frozen=True)
class CmdlineTools:
    tools: dict[CmdlineTool, str]

    def has(self, *tools: CmdlineTool) -> bool:
        return all(self.tools[tool] is not None for tool in tools)

    def require(self, *tools: CmdlineTool):
        for tool in tools:
            if not self.has(tool):
                raise SetupError(f"`{tool.value}` ({tool.name}) needed but not found in path")

    def warn_if_missing(self, *tools: CmdlineTool):
        for tool in tools:
            if not self.has(tool):
                log.warning(
                    "`%s` (%s) not found in path; it is recommended to install it for better functionality.",
                    tool.value,
                    tool.name,
                )


_tools_cache = TTLCache(maxsize=1, ttl=5.0)


@cached(_tools_cache)
def tool_check() -> CmdlineTools:
    tools = {}
    for tool in CmdlineTool:
        tools[tool] = shutil.which(tool.value)
    return CmdlineTools(tools)


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
        subprocess.run(["start", shlex.quote(filename)], shell=True)
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
        raise SetupError("ImageMagick `magick` not found in path; check it is installed?")
    if not _terminal_supports_sixel():
        raise SetupError("Terminal does not support Sixel graphics ({os.environ.get('TERM'})")

    try:
        cmd = ["magick", str(image_path), "-geometry", f"{width}x{height}", "sixel:-"]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise SetupError(f"Failed to display image: {e}")


def _terminal_show_image_kitty(filename: str | Path):
    filename = str(filename)
    try:
        subprocess.run(["kitty", "+kitten", "icat", filename])
    except subprocess.CalledProcessError as e:
        raise SetupError(f"Failed to display image with kitty: {e}")


def terminal_show_image(filename: str | Path):
    """
    Try to display an image in the terminal, using kitty or sixel.
    """
    if _terminal_is_kitty():
        _terminal_show_image_kitty(filename)
    elif _terminal_supports_sixel():
        _terminal_show_image_sixel(filename)
    else:
        raise SetupError("Image display in terminal not supported")


def terminal_show_image_graceful(filename: str | Path):
    try:
        terminal_show_image(filename)
    except SetupError:
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


def view_file_native(file_or_url: str | Path):
    """
    Open a file or URL in the user's preferred native application, falling back
    to pagination in console. For images, first tries terminal-based image display.
    """
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
        if file_ext_is_text(ext) or mime_type and mime_type.startswith("text"):
            view_file(file, use_less=num_lines > 40 or file_size > 20 * 1024)
        elif mime_type and mime_type.startswith("image"):
            try:
                terminal_show_image(file)
            except SetupError:
                native_open(file)
        else:
            native_open(file)
    elif os.path.isdir(file_or_url):
        native_open(file_or_url)
    else:
        raise FileNotFoundError(f"File does not exist: {file_or_url}")


def tail_file(filename: str | Path):
    """
    Tail a log file. With colorization using bat if available, otherwise using less.
    """
    filename = str(filename)
    quoted_filename = shlex.quote(filename)

    # Use bat if available.
    tool_check().require(CmdlineTool.less)
    tool_check().warn_if_missing(CmdlineTool.bat, CmdlineTool.tail)
    if tool_check().has(CmdlineTool.bat, CmdlineTool.tail, CmdlineTool.less):
        # Note bat doesn't have efficient seek functionality like `less +G` so we use less and bat.
        command = f"tail -10000 {quoted_filename} | bat --color=always --paging=never --style=plain --theme={BAT_THEME} -l log | less -R +G"
    else:
        command = f"less +G {quoted_filename}"

    log.message("Tailing file: `%s`", command)
    subprocess.run(command, shell=True, check=True)


def view_file(filename: str | Path, use_less: bool = True):
    """
    Displays a file in the console with pagination and syntax highlighting.
    """
    filename = str(filename)
    quoted_filename = shlex.quote(filename)

    # TODO: Visualize YAML frontmatter with different syntax/style than Markdown content.

    if tool_check().has(CmdlineTool.bat):
        command = f"bat --color=always --style=plain --theme={BAT_THEME} {quoted_filename}"
    else:
        tool_check().require(CmdlineTool.pygmentize)
        command = f"pygmentize -g {quoted_filename}"

    if use_less:
        command = f"{command} | less -R"

    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        output(f"Error displaying file: {e}", color=COLOR_ERROR)


def edit_files(*filenames: str | Path):
    """
    Edit a file using the user's preferred editor.
    """
    editor = os.getenv("EDITOR", get_settings().default_editor)
    subprocess.run([editor] + list(filenames))
