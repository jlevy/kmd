import shlex
from collections.abc import Callable
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

from pydantic.dataclasses import dataclass

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

    @classmethod
    def from_obj(
        cls,
        obj: "Action | Callable | str",
        args: Optional[List[str]] = None,
        options: Optional[Dict[str, str]] = None,
    ):
        from kmd.model.actions_model import Action

        if isinstance(obj, Action):
            name = obj.name
            type = CommandType.action
        elif isinstance(obj, Callable):
            name = obj.__name__
            type = CommandType.function
        elif isinstance(obj, str):
            name = obj
            type = CommandType.function
        else:
            raise ValueError(f"Invalid action or command: {obj}")

        return cls(name, type, args or [], options or {})

    def command_str(self) -> str:
        args_str = " ".join(shlex.quote(arg) for arg in self.args)
        options_str = " ".join(f"--{k}={shlex.quote(v)}" for k, v in self.options.items())
        return "`" + " ".join(filter(bool, [self.name, args_str, options_str])) + "`"

    def __str__(self):
        return self.command_str()
