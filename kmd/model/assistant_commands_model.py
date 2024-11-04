from textwrap import dedent
from typing import List

from pydantic import BaseModel

from kmd.util.parse_shell_args import format_command_str, parse_option


class Command(BaseModel):
    """
    A command that can be run on the console. It can be a function implementation
    in Python (like `show` or `files`) or correspond to an action.

    `args` is the list of string arguments, as they appear.

    `options` is a list of options, which are of the form `--name=value` for string
    options or `--name` for boolean options.

    Example:
    `transcribe resources/some-file.resource.yml --language=en --rerun`
    is represented as:
    {"name": "transcribe", "args": ["resources/some-file.resource.yml"], "options": ["--language=en", "--rerun"]}
    """

    name: str
    args: List[str]
    options: List[str]

    def full_str(self) -> str:
        parsed_options = [parse_option(option) for option in self.options]
        options_dict = {k: v for k, v in parsed_options}
        return format_command_str(self.name, self.args, options_dict)

    def __str__(self):
        return f"Command(`{self.full_str()}`)"


class SuggestedCommand(BaseModel):
    """
    A suggested command with an accompanying comment.
    """

    comment: str
    """
    Any additional notes about what this command does and why it may be useful.
    """

    command: Command
    """
    The command to be executed by the assistant. If it will run on the current selection,
    it may have no arguments. If it must run on a known file, it should be included as an
    argument. Options may also be specified if relevant.
    """

    def full_str(self) -> str:
        return dedent(
            f"""
            # {self.comment}
            {self.command.full_str()}
            """
        ).strip()
