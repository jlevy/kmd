"""
Platform-specific tools and utilities.
"""

import os
import shutil
from enum import Enum
from typing import Callable, Optional

from cachetools import cached, TTLCache
from pydantic.dataclasses import dataclass

from rich.text import Text
from xonsh.platform import ON_DARWIN, ON_LINUX, ON_WINDOWS

from kmd.config.logger import get_logger
from kmd.config.text_styles import EMOJI_WARN
from kmd.errors import SetupError
from kmd.shell.shell_output import (
    cprint,
    format_name_and_description,
    format_paragraphs,
    format_success_or_failure,
    Wrap,
)
from kmd.shell_tools.osc_tools import terminal_supports_osc8
from kmd.shell_tools.terminal_images import terminal_supports_sixel


log = get_logger(__name__)


class OSPlatform(Enum):
    macos = "macos"
    linux = "linux"
    windows = "windows"
    unknown = "unknown"


@cached({})
def detect_platform() -> OSPlatform:
    if ON_DARWIN:
        return OSPlatform.macos
    elif ON_LINUX:
        return OSPlatform.linux
    elif ON_WINDOWS:
        return OSPlatform.windows
    else:
        return OSPlatform.unknown


@dataclass(frozen=True)
class ToolDep:
    """
    Information about a tool dependency and how to install it.
    """

    command_names: tuple[str, ...]
    check_function: Optional[Callable[[], bool]] = None
    comment: Optional[str] = None

    brew_pkg: Optional[str] = None
    apt_pkg: Optional[str] = None
    pip_pkg: Optional[str] = None
    winget_pkg: Optional[str] = None


def check_libmagic():
    try:
        import magic

        magic.Magic()
        return True
    except Exception as e:
        log.info("libmagic is not installed or not accessible: %s", e)
        return False


class Tool(Enum):
    """
    External tools that we like to use.
    """

    # These are usually pre-installed on all platforms:
    less = ToolDep(("less",))
    tail = ToolDep(("tail",))

    pygmentize = ToolDep(
        ("pygmentize",),
        brew_pkg="pygments",
        apt_pkg="python3-pygments",
        pip_pkg="Pygments",
    )
    ripgrep = ToolDep(
        ("rg",),
        brew_pkg="ripgrep",
        apt_pkg="ripgrep",
        winget_pkg="BurntSushi.ripgrep",
    )
    bat = ToolDep(
        ("batcat", "bat"),  # batcat for Debian/Ubuntu), bat for macOS
        brew_pkg="bat",
        apt_pkg="bat",
        winget_pkg="sharkdp.bat",
    )
    libmagic = ToolDep(
        (),
        comment="""
          For macOS and Linux, brew or apt gives the latest binaries. For Windows, it may be
          easier to use pip.
        """,
        check_function=check_libmagic,
        brew_pkg="libmagic",
        apt_pkg="libmagic1",
        pip_pkg="python-magic-bin",
    )
    ffmpeg = ToolDep(
        ("ffmpeg",),
        brew_pkg="ffmpeg",
        apt_pkg="ffmpeg",
        winget_pkg="Gyan.FFmpeg",
    )
    imagemagick = ToolDep(
        ("magick",),
        brew_pkg="imagemagick",
        apt_pkg="imagemagick",
        winget_pkg="ImageMagick.ImageMagick",
    )

    @property
    def full_name(self) -> str:
        name = self.name
        if self.value.command_names:
            name += f" ({' or '.join(f'`{name}`' for name in self.value.command_names)})"
        return name


@dataclass(frozen=True)
class InstalledTools:
    """
    Info about which tools are installed.
    """

    tools: dict[Tool, str | bool]

    def has(self, *tools: Tool) -> bool:
        return all(self.tools[tool] is not None for tool in tools)

    def require(self, *tools: Tool):
        for tool in tools:
            if not self.has(tool):
                print_missing_tool_help(tool)
                raise SetupError(
                    f"`{tool.value}` ({tool.value.command_names}) needed but not found"
                )

    def missing_tools(self, *tools: Tool):
        if not tools:
            tools = tuple(Tool)
        return [tool for tool in tools if not self.tools[tool]]

    def warn_if_missing(self, *tools: Tool):
        for tool in self.missing_tools(*tools):
            print_missing_tool_help(tool)

    def formatted(self):
        texts = []
        for tool, path in self.tools.items():
            doc = format_success_or_failure(
                bool(path), true_str=f"Found: `{path}`", false_str="Not found!"
            )
            texts.append(format_name_and_description(tool.name, doc))

        return format_paragraphs(*texts)


def print_missing_tool_help(tool: Tool):
    cprint()
    cprint(
        "%s %s was not found; it is recommended to install it for better functionality.",
        EMOJI_WARN,
        tool.full_name,
    )
    if tool.value.comment:
        cprint(tool.value.comment, text_wrap=Wrap.WRAP_FULL)
    print_install_suggestion(tool)


def print_install_suggestion(*missing_tools: Tool):
    platform = detect_platform()
    brew_pkgs = [tool.value.brew_pkg for tool in missing_tools if tool.value.brew_pkg]
    apt_pkgs = [tool.value.apt_pkg for tool in missing_tools if tool.value.apt_pkg]
    winget_pkgs = [tool.value.winget_pkg for tool in missing_tools if tool.value.winget_pkg]
    pip_pkgs = [tool.value.pip_pkg for tool in missing_tools if tool.value.pip_pkg]

    if platform == OSPlatform.macos and brew_pkgs:
        cprint("On macOS, try using Homebrew: `brew install %s`", " ".join(brew_pkgs))
    elif platform == OSPlatform.linux and apt_pkgs:
        cprint(
            "On Linux, try using your package manager, e.g.: `sudo apt install %s`",
            " ".join(apt_pkgs),
        )
    elif platform == OSPlatform.windows and winget_pkgs:
        cprint("On Windows, try using Winget: `winget install %s`", " ".join(winget_pkgs))

    if pip_pkgs:
        cprint("You may also try using pip: `pip install %s`", " ".join(pip_pkgs))


_tools_cache = TTLCache(maxsize=1, ttl=5.0)


@cached(_tools_cache)
def tool_check() -> InstalledTools:
    tools: dict[Tool, str | bool] = {}

    def which_tool(tool: Tool) -> str | None:
        return next(filter(None, (shutil.which(name) for name in tool.value.command_names)), None)

    def check_tool(tool: Tool) -> bool:
        return bool(tool.value.check_function and tool.value.check_function())

    for tool in Tool:
        tools[tool] = which_tool(tool) or check_tool(tool)

    return InstalledTools(tools)


@dataclass(frozen=True)
class TerminalInfo:
    term: str
    term_program: str
    supports_sixel: bool
    supports_osc8: bool

    def as_text(self) -> Text:
        return Text.assemble(
            format_success_or_failure(
                self.supports_sixel, true_str="Sixel images", false_str="No Sixel images"
            ),
            ", ",
            format_success_or_failure(
                self.supports_osc8, true_str="OSC 8 hyperlinks", false_str="No OSC 8 hyperlinks"
            ),
        )

    def print_term_info(self):
        log.message(
            Text.assemble(
                f"Terminal is {self.term} ({self.term_program}): ",
                self.as_text(),
            )
        )


def check_terminal_features() -> TerminalInfo:
    return TerminalInfo(
        term=os.environ.get("TERM", ""),
        term_program=os.environ.get("TERM_PROGRAM", ""),
        supports_sixel=terminal_supports_sixel(),
        supports_osc8=terminal_supports_osc8(),
    )
