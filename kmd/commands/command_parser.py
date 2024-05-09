from collections import namedtuple
from dataclasses import dataclass
import logging
from typing import Dict, List, NewType
from lark import Lark, Token, Transformer, v_args

from kmd.util.url_utils import Url

log = logging.getLogger(__name__)


@dataclass
class Command:
    action: str
    options: Dict[str, str]
    arguments: List[Url | str]


Option = namedtuple("Option", ["name", "value"])


GRAMMAR = r"""

    // A command is simply an action and possibly options and arguments.
    command: SPACE? action (SPACE option)* (SPACE argument)* SPACE?

    action: NAME

    // Single-dash style command line arguments only.
    option: "-" NAME "=" string

    // An argument could be a file path or a URL.
    argument: string  

    string: ARG_STRING | ESCAPED_STRING

    NAME: /[a-zA-Z0-9_]+/
    ARG_STRING: /[^-\s][^\s]*/  // An argument can't start with a dash.
    SPACE: (" "|/\t/)+  // Inline spaces only.

    UNESCAPED_STRING: /[^\s'"]+/
    // Escaped string can be single or double quoted. (based on common.lark):
    _STRING_INNER: /.*?/
    _STRING_ESC_INNER: _STRING_INNER /(?<!\\)(\\\\)*?/
    ESCAPED_STRING : "\"" _STRING_ESC_INNER "\"" | "'" _STRING_ESC_INNER "'"

"""


def is_space_token(item):
    return isinstance(item, Token) and item.type == "SPACE"


def trim_escaped_string(s: str):
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    return s


class CommandTransformer(Transformer):
    @v_args(inline=True)
    def action(self, action):
        return str(action)

    @v_args(inline=True)
    def option(self, name, value):
        return Option(str(name), trim_escaped_string(str(value.children[0])))

    @v_args(inline=True)
    def argument(self, argument):
        return trim_escaped_string(str(argument.children[0]))

    def command(self, items):
        filtered_items = [item for item in items if not is_space_token(item)]
        action = str(filtered_items[0])
        options = {}
        arguments = []
        for part in filtered_items[1:]:
            if isinstance(part, Option):
                options[part.name] = part.value
            else:
                arguments.append(part)
        return Command(action=action, options=options, arguments=arguments)


parser = Lark(GRAMMAR, start="command")


def parse_command(command: str):
    try:
        tree = parser.parse(command)
        # print("Tree:", tree.pretty())
        command = CommandTransformer().transform(tree)
        return command
    except Exception as e:
        log.info(f"Error parsing command: {e}")
        raise ValueError(f"Invalid command: {e}")


def test_command_parsing():
    test_cases = [
        ("list", Command(action="list", options={}, arguments=[])),
        (" list", Command(action="list", options={}, arguments=[])),
        ("list  ", Command(action="list", options={}, arguments=[])),
        ("list foo*", Command(action="list", options={}, arguments=["foo*"])),
        ("list 'foo*'", Command(action="list", options={}, arguments=["foo*"])),
        ('list "foo*"', Command(action="list", options={}, arguments=["foo*"])),
        (
            "list -arg1=aaa -arg2=bbb ccc",
            Command(action="list", options={"arg1": "aaa", "arg2": "bbb"}, arguments=["ccc"]),
        ),
        (
            "download http://example.com",
            Command(action="download", options={}, arguments=["http://example.com"]),
        ),
        (
            "save -path=/some/example",
            Command(action="save", options={"path": "/some/example"}, arguments=[]),
        ),
        (
            ' save  -path="/some/example" ',
            Command(action="save", options={"path": "/some/example"}, arguments=[]),
        ),
        (
            "list https://example.com",
            Command(action="list", options={}, arguments=["https://example.com"]),
        ),
    ]

    for cmd, expected in test_cases:
        parsed_command = parse_command(cmd)
        assert (
            parsed_command == expected
        ), f"Command '{cmd}' expected {expected} but got {parsed_command}"
