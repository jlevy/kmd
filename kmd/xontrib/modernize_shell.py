import subprocess

from xonsh.built_ins import XSH

from kmd.shell_tools.tool_deps import Tool, tool_check


def modernize_shell() -> None:
    """
    Add various widely used aliases and tools to improve and modernize the shell
    experience, if they are installed.
    """
    enable_zoxide()
    add_modern_aliases()


def enable_zoxide() -> None:
    installed_tools = tool_check()

    if installed_tools.has(Tool.zoxide):
        assert XSH.builtins
        zoxide_init = subprocess.check_output(["zoxide", "init", "xonsh"]).decode()
        XSH.builtins.execx(zoxide_init, "exec", XSH.ctx, filename="zoxide")


def add_modern_aliases() -> None:
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
