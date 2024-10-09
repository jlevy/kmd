import re
from collections.abc import Callable
from typing import Dict, Iterable, List, Optional, TYPE_CHECKING

from pydantic.dataclasses import dataclass

from kmd.util.parse_shell_args import format_command_str, parse_command_str


if TYPE_CHECKING:
    from kmd.model.actions_model import Action


def is_assist_request_str(line: str) -> Optional[str]:
    """
    Is this a query to the assistant?
    Checks for phrases ending in a ? or a period, or starting with a ?.
    """
    line = line.strip()
    if re.search(r"\b\w+\.$", line) or re.search(r"\b\w+\?$", line) or line.startswith("?"):
        return line.lstrip("?").strip()
    return None


def assist_request_str(request: str) -> str:
    """
    Command string to call the assistant.
    """
    return f"? {request}"


@dataclass
class Command:
    """
    A command that can be run on the console. It can be a function implementation
    in Python (like `show` or `files`) or correspond to an action.

    `args` is the list of string arguments, as they appear.

    `options` is a dictionary of options. Options with values will have a string value.
    Options without values will be treated as boolean flags.
    """

    name: str
    args: List[str]
    options: Dict[str, str | bool]

    @classmethod
    def from_command_str(cls, command_str: str) -> "Command":
        name, args, options = parse_command_str(command_str)
        return cls(name, args, options)

    @classmethod
    def from_obj(
        cls,
        obj: "Action | Callable | str",
        args: Optional[Iterable[str]] = None,
        options: Optional[Dict[str, str]] = None,
    ):
        from kmd.model.actions_model import Action

        if isinstance(obj, Action):
            name = obj.name
        elif isinstance(obj, Callable):
            name = obj.__name__
        elif isinstance(obj, str):
            name = obj
        else:
            raise ValueError(f"Invalid action or command: {obj}")

        return cls(name, list(args or []), dict(options or {}))

    def command_str(self) -> str:
        return format_command_str(self.name, self.args, self.options)

    def __str__(self):
        return self.command_str()
