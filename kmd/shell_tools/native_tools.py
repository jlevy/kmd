"""
Platform-specific tools and utilities.
"""

import os
import shlex
import subprocess
import webbrowser
from enum import Enum
from pathlib import Path
from typing import Tuple


from kmd.config.logger import get_logger
from kmd.config.text_styles import (
    BAT_STYLE,
    BAT_THEME,
    COLOR_ERROR,
)
from kmd.errors import FileNotFound, SetupError
from kmd.model.args_model import fmt_loc
from kmd.model.file_formats_model import file_format_info, is_full_html_page, read_partial_text
from kmd.shell.shell_output import cprint, Wrap
from kmd.shell_tools.terminal_images import terminal_show_image
from kmd.shell_tools.tool_deps import Tool, OSPlatform, detect_platform, tool_check
from kmd.util.log_calls import log_calls
from kmd.util.url import as_file_url, is_file_url, is_url


log = get_logger(__name__)


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
    platform = detect_platform()
    if platform == OSPlatform.macos:
        subprocess.run(["open", filename])
    elif platform == OSPlatform.linux:
        subprocess.run(["xdg-open", filename])
    elif platform == OSPlatform.windows:
        subprocess.run(["start", shlex.quote(filename)], shell=True)
    else:
        raise NotImplementedError("Unsupported platform")


class ViewMode(Enum):
    auto = "auto"
    console = "console"
    browser = "browser"
    native = "native"
    terminal_image = "terminal_image"


@log_calls(level="info")
def _detect_view_mode(file_or_url: str) -> ViewMode:
    # As a heuristic, we use the browser for URLs and for local files that are
    # clearly full HTML pages (since HTML fragments are fine on console).
    if is_url(file_or_url) and not is_file_url(file_or_url):
        return ViewMode.browser

    path = Path(file_or_url)
    if path.is_file():  # File or symlink.
        content = read_partial_text(path)
        if content and is_full_html_page(content):
            return ViewMode.browser

        info = file_format_info(path)
        log.info("File format detected: %s", info)

        if info.is_text:
            return ViewMode.console
        if info.is_image:
            log.info("Detected image file, will display in terminal")
            return ViewMode.terminal_image
        else:
            return ViewMode.native
    elif path.is_dir():
        return ViewMode.native
    else:
        raise FileNotFound(fmt_loc(file_or_url))


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
            raise FileNotFound(fmt_loc(path))

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
        except SetupError as e:
            log.info("%s: %s", e, path)
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
    tool_check().require(Tool.less)
    tool_check().warn_if_missing(Tool.bat, Tool.tail)
    if tool_check().has(Tool.bat, Tool.tail, Tool.less):
        # Note bat doesn't have efficient seek functionality like `less +G` so we use less and bat.
        command = f"tail -10000 {quoted_filename} | bat --color=always --paging=never --style=plain --theme={BAT_THEME} -l log | less -R +G"
    else:
        command = f"less +G {quoted_filename}"

    cprint("Tailing file: `%s`", command, text_wrap=Wrap.NONE)
    subprocess.run(command, shell=True, check=True)


def view_file_console(filename: str | Path, use_pager: bool = True):
    """
    Displays a file in the console with pagination and syntax highlighting.
    """
    filename = str(filename)
    quoted_filename = shlex.quote(filename)

    # TODO: Visualize YAML frontmatter with different syntax/style than Markdown content.

    tool_check().require(Tool.less)
    if tool_check().has(Tool.bat):
        pager_str = "--pager=always --pager=less " if use_pager else ""
        command = f"bat {pager_str}--color=always --style={BAT_STYLE} --theme={BAT_THEME} {quoted_filename}"
    else:
        tool_check().require(Tool.pygmentize)
        command = f"pygmentize -g {quoted_filename}"
        if use_pager:
            command = f"{command} | less -R"

    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        cprint(f"Error displaying file: {e}", color=COLOR_ERROR)


def edit_files(*filenames: str | Path):
    """
    Edit a file using the user's preferred editor.
    """
    from kmd.config.settings import global_settings

    editor = os.getenv("EDITOR", global_settings().default_editor)
    subprocess.run([editor] + list(filenames))


def native_trash(*paths: str | Path):
    from send2trash import send2trash

    send2trash(list(Path(p) for p in paths))
