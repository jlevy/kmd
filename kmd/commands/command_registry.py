from typing import Callable, List
from kmd.config.logger import get_logger

log = get_logger(__name__)


_commands: List[Callable] = []


def kmd_command(func):
    _commands.append(func)
    return func


def all_commands():
    return sorted(_commands, key=lambda cmd: cmd.__name__)
