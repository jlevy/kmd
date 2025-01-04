from xonsh.built_ins import XSH

from kmd.shell_tools.tool_deps import Tool, tool_check


def add_modern_aliases() -> None:
    """
    Miscellaneous aliases to improve and modernize shell experience,
    if they are installed.
    """
    installed_tools = tool_check()

    assert XSH.aliases

    if installed_tools.has(Tool.eza):
        XSH.aliases["ls"] = ["eza", "--group-directories-first", "-F"]
        XSH.aliases["ll"] = ["eza", "--group-directories-first", "-F", "-l"]
        XSH.aliases["lla"] = ["eza", "--group-directories-first", "-F", "-la"]


# TODO:
# - find -> fd
# - cat -> bat
# - grep -> rg
# - du -> dust
# - df -> duf
# - ps -> procs
# - top -> btm
