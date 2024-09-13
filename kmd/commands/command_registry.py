from typing import Any, Callable, Dict

from kmd.config.logger import get_logger

from kmd.errors import InvalidInput

log = get_logger(__name__)


CommandFunction = Callable[..., Any]

_commands: Dict[str, CommandFunction] = {}


def kmd_command(func: CommandFunction) -> CommandFunction:
    _commands[func.__name__] = func
    return func


def all_commands() -> Dict[str, CommandFunction]:
    """
    All commands, sorted by name.
    """
    return dict(sorted(_commands.items()))


def look_up_command(name: str) -> CommandFunction:
    cmd = _commands.get(name)
    if not cmd:
        raise InvalidInput(f"Command `{name}` not found")
    return cmd
