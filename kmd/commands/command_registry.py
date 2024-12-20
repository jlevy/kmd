from typing import Any, Callable, Dict

from kmd.config.logger import get_logger

from kmd.errors import InvalidInput

log = get_logger(__name__)


CommandFunction = Callable[..., Any]

_commands: Dict[str, CommandFunction] = {}


def kmd_command(func: CommandFunction) -> CommandFunction:
    """
    Decorator to register a command.
    """
    if func.__name__ in _commands:
        log.error("Command `%s` already registered; duplicate definition?", func.__name__)
    _commands[func.__name__] = func
    return func


def register_all_commands() -> None:
    """
    Ensure all commands are registered and imported.
    """
    import kmd.commands  # noqa: F401

    log.info("Command registry: %d commands registered.", len(_commands))


def all_commands() -> Dict[str, CommandFunction]:
    """
    All commands, sorted by name.
    """
    register_all_commands()
    return dict(sorted(_commands.items()))


def look_up_command(name: str) -> CommandFunction:
    cmd = _commands.get(name)
    if not cmd:
        raise InvalidInput(f"Command `{name}` not found")
    return cmd
