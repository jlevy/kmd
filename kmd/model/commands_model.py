import re
from collections.abc import Callable
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING

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


def stringify_non_bool(value: Any) -> str | bool:
    if isinstance(value, bool):
        return value
    else:
        return str(value)


@dataclass
class Command:
    """
    A command that can be run in the shell, saved to history, etc.

    `args` is the list of arguments, as they appear in string form on the command line.

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
    def assemble(
        cls,
        callable: "Action | Callable | str",
        args: Optional[Iterable[Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ):
        """
        Assemble a serializable Command from any Action, Callable, or string and
        args and option values. Values can be provided as values or as string values.

        Options that are None or False are dropped as they are interpreted to mean
        omitted optional params or disabled boolean flags.
        """
        from kmd.model.actions_model import Action

        if isinstance(callable, Action):
            name = callable.name
        elif isinstance(callable, Callable):
            name = callable.__name__
        elif isinstance(callable, str):
            name = callable
        else:
            raise ValueError(f"Invalid action or command: {callable}")

        if args and None in args:
            raise ValueError("None is not a valid argument value.")

        # Ensure values are stringified.
        str_args: List[str] = []
        if args:
            str_args = [str(arg) for arg in args]

        # Ensure options are stringified or boolean options.
        # Skip None values, which are omitted optional params.

        str_options: Dict[str, str | bool] = {}
        if options:
            str_options = {
                k: stringify_non_bool(v)
                for k, v in options.items()
                if v is not None and v is not False
            }

        return cls(name, str_args, str_options)

    def command_str(self) -> str:
        return format_command_str(self.name, self.args, self.options)

    def __str__(self):
        return self.command_str()
