"""
Platform-specific tools and utilities.
"""

import os
import shlex
import shutil
import subprocess
import webbrowser
from enum import Enum
from pathlib import Path
from typing import Tuple

from cachetools import cached, TTLCache
from pydantic.dataclasses import dataclass
from xonsh.platform import ON_DARWIN, ON_LINUX, ON_WINDOWS

from kmd.config.logger import get_logger
from kmd.config.text_styles import (
    BAT_STYLE,
    BAT_THEME,
    COLOR_ERROR,
    COLOR_HINT,
    EMOJI_FALSE,
    EMOJI_TRUE,
)
from kmd.errors import FileNotFound, SetupError
from kmd.model.file_formats_model import (
    detect_mime_type,
    is_full_html_page,
    parse_file_ext,
    read_partial_text,
)
from kmd.shell.shell_output import format_name_and_description, format_paragraphs, output, Wrap
from kmd.util.format_utils import fmt_path
from kmd.util.url import as_file_url, is_url


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

    def formatted(self):
        texts = []
        for tool, path in self.tools.items():
            if path:
                doc = f"{EMOJI_TRUE} Found: `{path}`"
            else:
                doc = f"{EMOJI_FALSE} Not found! Consider installing this tool."
            texts.append(format_name_and_description(tool.name, doc))

        return format_paragraphs(*texts)


_tools_cache = TTLCache(maxsize=1, ttl=5.0)


@cached(_tools_cache)
def tool_check() -> CmdlineTools:
    tools = {}
    for tool in CmdlineTool:
        tools[tool] = shutil.which(tool.value)
    return CmdlineTools(tools)


def file_size_check(
    filename: str | Path, max_lines: int = 100, max_bytes: int = 50 * 1024
) -> Tuple[int, int]:
    """
    Get the size and scan to get initial line count (up to max_lines) of a file.
    """
    filename = str(filename)
    file_size = os.path.getsize(filename)
    line_min = 0
    with open(filename, "rb") as f:
        for i, _line in enumerate(f):
            if i >= max_lines or f.tell() > max_bytes:
                break
            line_min += 1
    return file_size, line_min


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
    term_program = os.environ.get("TERM_PROGRAM", "")
    supported_terms = ["xterm", "xterm-256color", "screen.xterm-256color", "kitty", "iTerm.app"]

    term_supports = any(supported_term in term for supported_term in supported_terms)

    # TODO: Not working currently. Get hyper-k Hyper plugin to fix this?
    term_program_supports = term_program not in ["Hyper"]

    return term_supports and term_program_supports


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
    Raise `SetupError` if not supported.
    """
    if _terminal_is_kitty():
        _terminal_show_image_kitty(filename)
    elif _terminal_supports_sixel():
        _terminal_show_image_sixel(filename)
    else:
        raise SetupError("Image display in this terminal doesn't seem to be supported")


def terminal_show_image_graceful(filename: str | Path):
    try:
        terminal_show_image(filename)
    except SetupError:
        output(f"[Image: {filename}]", color=COLOR_HINT)


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


class ViewMode(Enum):
    auto = "auto"
    console = "console"
    browser = "browser"
    native = "native"
    terminal_image = "terminal_image"


def _detect_view_mode(file_or_url: str) -> ViewMode:
    # As a heuristic, we use the browser for URLs and for local files that are
    # clearly full HTML pages (since HTML fragments are fine on console).
    if is_url(file_or_url):
        return ViewMode.browser

    path = Path(file_or_url)
    if path.is_file():  # File or symlink.
        content = read_partial_text(path)
        if content and is_full_html_page(content):
            return ViewMode.browser

        mime_type = detect_mime_type(path)
        ext = parse_file_ext(path)
        is_text = (ext and ext.is_text()) or mime_type and mime_type.startswith("text")

        if is_text or (mime_type and mime_type.startswith("text")):
            return ViewMode.console

        if mime_type and mime_type.startswith("image"):
            return ViewMode.terminal_image

        return ViewMode.native
    elif path.is_dir():
        return ViewMode.native
    else:
        raise FileNotFound(fmt_path(file_or_url))


def view_file_native(
    file_or_url: str | Path,
    view_mode: ViewMode = ViewMode.auto,
):
    """
    Open a file or URL in the console or a native app. If `view_mode` is auto,
    automaticallyd determine whether to use console, web browser, or the user's
    preferred native application. For images, also tries terminal-based image
    display.
    """
    file_or_url = str(file_or_url)
    if not is_url(file_or_url):
        path = Path(file_or_url)
        if not path.exists():
            raise FileNotFound(fmt_path(path))

    if view_mode == ViewMode.auto:
        view_mode = _detect_view_mode(file_or_url)

    if view_mode == ViewMode.browser:
        url = file_or_url if is_url(file_or_url) else as_file_url(file_or_url)
        log.message("Opening URL in browser: %s", url)
        webbrowser.open(url)
    elif view_mode == ViewMode.console:
        file_size, min_lines = file_size_check(path)
        view_file_console(path, use_pager=min_lines > 40 or file_size > 20 * 1024)
    elif view_mode == ViewMode.terminal_image:
        try:
            terminal_show_image(path)
        except SetupError:
            native_open(path)
    elif view_mode == ViewMode.native:
        native_open(file_or_url)


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

    output("Tailing file: `%s`", command, text_wrap=Wrap.NONE)
    subprocess.run(command, shell=True, check=True)


def view_file_console(filename: str | Path, use_pager: bool = True):
    """
    Displays a file in the console with pagination and syntax highlighting.
    """
    filename = str(filename)
    quoted_filename = shlex.quote(filename)

    # TODO: Visualize YAML frontmatter with different syntax/style than Markdown content.

    tool_check().require(CmdlineTool.less)
    if tool_check().has(CmdlineTool.bat):
        pager_str = "--pager=always --pager=less " if use_pager else ""
        command = f"bat {pager_str}--color=always --style={BAT_STYLE} --theme={BAT_THEME} {quoted_filename}"
    else:
        tool_check().require(CmdlineTool.pygmentize)
        command = f"pygmentize -g {quoted_filename}"
        if use_pager:
            command = f"{command} | less -R"

    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        output(f"Error displaying file: {e}", color=COLOR_ERROR)


def edit_files(*filenames: str | Path):
    """
    Edit a file using the user's preferred editor.
    """
    from kmd.config.settings import global_settings

    editor = os.getenv("EDITOR", global_settings().default_editor)
    subprocess.run([editor] + list(filenames))
