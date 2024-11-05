import re
from collections.abc import Callable
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, field_validator

from kmd.util.format_utils import single_line
from kmd.util.log_calls import quote_if_needed
from kmd.util.parse_shell_args import (
    format_command_str,
    format_options,
    parse_command_str,
    parse_option,
    StrBoolOptions,
)


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
    return f"? {quote_if_needed(request)}"


def stringify_non_bool(value: Any) -> str | bool:
    if isinstance(value, bool):
        return value
    else:
        return str(value)


class Command(BaseModel):
    """
    A command that can be run in the shell, saved to history, etc.
    We keep options unparsed in persisted form for convenience with serialization
    and use with LLMs structured outputs.

    Example:
    `transcribe resources/some-file.resource.yml --language=en --rerun`
    is represented as:
    {"name": "transcribe", "args": ["resources/some-file.resource.yml"], "options": ["--language=en", "--rerun"]}

    """

    name: str

    args: List[str]
    """
    The list of arguments, as they appear in string form on the command line.
    """

    options: List[str]
    """
    `options` is a list of options in string format, i.e. `--name=value` for string
    options or `--name` for boolean options.
    """

    @property
    def parsed_options(self) -> StrBoolOptions:
        """
        Return a dictionary of options. Command-line options with values are represented
        with a string value. Command-line options present but without a value are represented
        as a boolean True.
        """
        parsed_options = [parse_option(option) for option in self.options]
        return {k: v for k, v in parsed_options}

    @classmethod
    def from_command_str(cls, command_str: str) -> "Command":
        name, args, options = parse_command_str(command_str)
        return cls(name=name, args=args, options=format_options(options))

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

        str_options: StrBoolOptions = {}
        if options:
            str_options = {
                k: stringify_non_bool(v)
                for k, v in options.items()
                if v is not None and v is not False
            }

        return cls(name=name, args=str_args, options=format_options(str_options))

    def command_str(self) -> str:
        return format_command_str(self.name, self.args, self.parsed_options)

    def __str__(self):
        return f"Command(`{self.command_str()}`)"


class CommentedCommand(BaseModel):
    """
    A command with an optional comment explaining what it does.
    """

    comment: Optional[str]
    """
    Any additional notes about what this command does and why it may be useful.
    Should be a single line of text.
    """

    command: Command
    """
    The command to be executed by the assistant. If it will run on the current selection,
    it may have no arguments. If it must run on a known file, it should be included as an
    argument. Options may also be specified if relevant.
    """

    @field_validator("comment")
    def clean_comment(cls, v: str) -> str:
        return single_line(v)

    def script_str(self) -> str:
        if self.comment:
            return "\n".join(
                [
                    f"# {self.comment}",
                    self.command.command_str(),
                ]
            )
        else:
            return self.command.command_str()
