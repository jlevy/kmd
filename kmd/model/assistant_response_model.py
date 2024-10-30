from textwrap import dedent
from typing import List, Optional

from pydantic import BaseModel

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
    commentary: Optional[str]
    """
    The Markdown-formatted text response from the assistant. Should include
    only the assistant's initial response and commentary, *not* any specific
    output or commands.

    If there is a simple direct answer to the question and no commentary is
    needed, then make this blank and use `answer_text` instead.
    """

    answer_text: Optional[str]
    """
    Text that is a direct answer to the question by the assistant, if applicable.
    Leave this blank if the answer is just commentary!

    This is not commentary. It should not say the same thing as the commentary.
    It is the answer or the text requested. It should be in a form that the user
    could copy or use in another context, if desired.

    If the answer is complex, you may include Markdown formatting. Do not
    include any other commentary in `answer_text`.

    This can be blank if the response is only commentary.
    """

    suggested_commands: List[SuggestedCommand]
    """
    Commands that the assistant suggests to solve the user's request.
    These should be in the order the user should execute them.
    This can be empty if the assistant has no commands to suggest.
    """

    see_also: List[str]
    """
    Other commands that may be relevant but were not suggested as a solution.
    This should not include commands that were already suggested.
    This usually should not be empty since the assistant can also suggest
    related commands and help pages.
    """
