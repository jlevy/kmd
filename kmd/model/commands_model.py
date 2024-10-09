import re
import shlex
from collections.abc import Callable
from typing import Dict, Iterable, List, Optional, TYPE_CHECKING

from pydantic.dataclasses import dataclass


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
    A command that can be run on the console. It can be a basic function implementation
    (like `show` or `files`) or correspond to an action.

    Can be a parsed command or a natural language query to the assistant.
    """

    name: str
    args: List[str]
    options: Dict[str, str]

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

        return cls(name, list(args or []), options or {})

    def command_str(self) -> str:
        args_str = " ".join(shlex.quote(arg) for arg in self.args)
        options_str = " ".join(f"--{k}={shlex.quote(v)}" for k, v in self.options.items())
        return "`" + " ".join(filter(bool, [self.name, args_str, options_str])) + "`"

    def __str__(self):
        return self.command_str()
