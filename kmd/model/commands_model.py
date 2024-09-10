import shlex
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from kmd.model.actions_model import Action


class CommandType(Enum):
    function = "function"
    action = "action"


@dataclass
class Command:
    """
    A command that can be run on the console. It can be a basic function implementation
    (like `show` or `files`) or correspond to an action.
    """

    name: str
    type: CommandType
    args: List[str]
    options: Dict[str, str]

    def __init__(
        self,
        action_or_command: "Action | Callable | str",
        args: Optional[List[str]] = None,
        options: Optional[Dict[str, str]] = None,
    ):
        from kmd.model.actions_model import Action

        if isinstance(action_or_command, Action):
            self.name = action_or_command.name
            self.type = CommandType.action
        elif isinstance(action_or_command, Callable):
            self.name = action_or_command.__name__
            self.type = CommandType.function
        elif isinstance(action_or_command, str):
            self.name = action_or_command
            self.type = CommandType.function
        else:
            raise ValueError(f"Invalid action or command: {action_or_command}")

        self.args = args or []
        self.options = options or {}

    def command_str(self) -> str:
        args_str = " ".join(shlex.quote(arg) for arg in self.args)
        options_str = " ".join(f"--{k}={shlex.quote(v)}" for k, v in self.options.items())
        return "`" + " ".join(filter(bool, [self.name, args_str, options_str])) + "`"

    def __str__(self):
        return self.command_str()
