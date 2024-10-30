from enum import Enum
from textwrap import dedent
from typing import List

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


class Confidence(str, Enum):
    """
    How confident the assistant is that the answer is correct.
    """

    direct_answer = "direct_answer"
    """
    This response is a direct answer to the user's question.
    """

    partial_answer = "partial_answer"
    """
    This response is a partial answer to the user's question.
    """

    conversation = "conversation"
    """
    This response is conversational, not a direct answer to a user's question.
    """

    info_request = "info_request"
    """
    This response is a request for more information from the user.
    """

    unsure = "unsure"
    """
    This assistant is unsure of how to respond or answer the question.
    """


class AssistantResponse(BaseModel):
    response_text: str
    """
    Put the answer to the user's question here.

    If the user's last message was a question, and there is a clear answer,
    this should be a direct answer to the question and confidence should be
    `direct_answer`.
    
    If the answer is not complete, confidence should be
    `partial_answer`.

    If answering the last message would would require more information,
    this response text should be one or more questions to get the information
    needed and the confidence should be `info_request`.

    If the user is being conversational, this response text should be a
    response to the user's message and the confidence should be `conversation`.

    If the assistant is unsure of how to respond, confidence should be `unsure`.
    """

    confidence: Confidence
    """
    What is the nature of this response? Is it a direct answer, a partial answer,
    a conversational response, or a request for more information?
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
