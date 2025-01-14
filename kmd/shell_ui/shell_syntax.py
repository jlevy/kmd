import builtins
import re
from pathlib import Path
from typing import Optional

from xonsh.built_ins import XSH

from kmd.util.parse_shell_args import shell_quote


def is_assist_request_str(line: str) -> Optional[str]:
    """
    Is this a query to the assistant?
    Checks for phrases ending in a ? or starting with a ?.
    """
    line = line.strip()
    if re.search(r"\b\w+\?$", line) or line.startswith("?"):
        return line.lstrip("?").strip()
    return None


def assist_request_str(nl_req: str) -> str:
    """
    Command string to call the assistant with a natural language request.
    """
    nl_req = nl_req.lstrip("? ").rstrip()
    # Quoting isn't necessary unless we have quote marks.
    if "'" in nl_req or '"' in nl_req:
        return f"? {shell_quote(nl_req, idempotent=True)}"
    else:
        return f"? {nl_req}"


def is_valid_command(command_name: str, path: list[str]) -> bool:
    """
    Is this a valid command xonsh will understand, given current path
    and all loaded commands?
    """

    from xonsh.xoreutils._which import which, WhichError

    # Built-in values and aliases are allowed.
    python_builtins = dir(builtins)
    xonsh_builtins = dir(XSH.builtins)
    globals = XSH.ctx
    aliases = XSH.aliases or {}
    if (
        command_name in python_builtins
        or command_name in xonsh_builtins
        or command_name in globals
        or command_name in aliases
    ):
        return True

    # Directories are allowed since we have auto-cd on.
    if Path(command_name).is_dir():
        return True

    # Finally check if it is a known command.
    try:
        which(command_name, path=path)
        return True
    except WhichError:
        return False
