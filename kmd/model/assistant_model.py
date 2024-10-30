from textwrap import dedent
from typing import List

from pydantic import BaseModel

from kmd.shell.shell_output import print_assistance
from kmd.text_formatting.markdown_normalization import wrap_markdown
from kmd.util.parse_shell_args import format_command_str, parse_option


class Command(BaseModel):
    """
    A command that can be run on the console. It can be a function implementation
    in Python (like `show` or `files`) or correspond to an action.

    `args` is the list of string arguments, as they appear.

    `options` is list of options, which are of the form `--name=value` for string
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


# FIXME: Improve assistant model. Also let it output a sample doc that is not
# just a list of commands.
#
# class InputType(Enum):
#     item = "item"


# class NeededInput(BaseModel):
#     name: str
#     description: str


# class Intention(BaseModel):
#     goal_description: str
#     """
#     A description of the goal the user wants to achieve.
#     """

#     inputs: List[NeededInput]
#     """
#     Input values that the assistant needs from the user.
#     """


class SuggestedCommand(BaseModel):
    comment: str
    """
    Any additional notes about what this command does and when why it may be useful.
    """

    command: Command
    """
    The command to be executed by the assistant. If it will run on the current selection,
    it may have no arguments.
    If it must run on a known file, it should be included as an argument.
    Options may also be specified if relevant.
    """

    def full_str(self) -> str:
        return dedent(
            f"""
            # {self.comment}
            {self.command.full_str()}
            """
        ).strip()


class AssistantResponse(BaseModel):
    commentary: str
    """The text response from the assistant."""

    suggested_commands: List[SuggestedCommand]
    """
    Commands that the assistant suggests to solve the user's request.
    These should be in the order 
    """

    see_also: List[str]
    """
    Other commands that may be relevant but were not suggested as a solution.
    This may be empty.
    """

    # FIXME: Format prettier.
    def print(self) -> None:
        parts = []

        parts.append(wrap_markdown(self.commentary.strip()))

        if self.suggested_commands:
            formatted_commands = "\n\n".join(c.full_str() for c in self.suggested_commands)
            parts.append(f"Suggested commands:\n\n```\n{formatted_commands}\n```")

        if self.see_also:
            formatted_see_also = ", ".join(f"`{cmd}`" for cmd in self.see_also)
            see_also_str = f"See also: {formatted_see_also}"
            parts.append(see_also_str)

        final_output = "\n\n".join(parts)

        print_assistance(final_output)
