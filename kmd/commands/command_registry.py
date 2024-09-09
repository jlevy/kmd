from typing import Any, Callable, Dict, List

from kmd.config.logger import get_logger

log = get_logger(__name__)


CommandFunction = Callable[..., Any]

_commands: List[CommandFunction] = []


def kmd_command(func: CommandFunction) -> CommandFunction:
    _commands.append(func)
    return func


def all_commands() -> Dict[str, CommandFunction]:
    """
    All commands, sorted by name.
    """
    return {cmd.__name__: cmd for cmd in sorted(_commands, key=lambda cmd: cmd.__name__)}
