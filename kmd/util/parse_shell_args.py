"""
Tiny parsing library for parsing and writing shell commands, using a simplified
shell syntax that is compatible with Python and xonsh (but not quite the same
as bash!).
"""

import ast
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

# Same unsafe chars as shlex.quote().
_shell_unsafe_re = re.compile(r"[^\w@%+=:,./-]", re.ASCII)


def shell_quote(arg: str) -> str:
    """
    Quote a string for shell usage, if needed, using simplified shell conventions
    compatible with Python and xonsh. This means simple text words without spaces
    are left unquoted. Prefers double quotes in cases where either could work.
    """
    has_unsafe = _shell_unsafe_re.search(arg)
    if arg and not has_unsafe:
        return arg
    elif '"' not in arg:
        return f'"{arg}"'
    else:
        return repr(arg)


def shell_unquote(arg: str) -> str:
    """
    Unquote a string using Python conventions, but allow unquoted strings to
    pass through.
    """
    if arg.startswith(("'", '"')) and arg.endswith(arg[0]):
        try:
            return ast.literal_eval(arg)
        except (SyntaxError, ValueError):
            pass
    return arg


def shell_split(command_str: str) -> List[str]:
    """
    Split a command string into tokens, respecting quotes and backslash escapes.
    """
    tokens = []
    current_token = ""
    in_quote = False
    quote_char = ""
    escape = False
    i = 0
    while i < len(command_str):
        c = command_str[i]
        if escape:
            current_token += c
            escape = False
        elif c == "\\":
            current_token += c
            escape = True
        elif in_quote:
            current_token += c
            if c == quote_char:
                in_quote = False
        elif c in ('"', "'"):
            current_token += c
            in_quote = True
            quote_char = c
        elif c.isspace():
            if current_token:
                tokens.append(current_token)
                current_token = ""
        else:
            current_token += c
        i += 1

    if current_token:
        tokens.append(current_token)

    return tokens


def format_command_str(command: str, args: Iterable[str], options: Dict[str, str | bool]) -> str:
    """
    Format a command string using simplified shell conventions (compatible with Python and xonsh).
    """
    args_str = " ".join(shell_quote(arg) for arg in args)
    options_str = " ".join(
        f"--{k}={shell_quote(v)}" if isinstance(v, str) else f"--{k}" for k, v in options.items()
    )
    return " ".join(filter(bool, [command, args_str, options_str]))


def parse_option(key_value_str: str) -> Tuple[str, str | bool]:
    """
    Parse a key-value string like `--foo=123` or `--bar="some value"` into a `(key, value)`
    tuple.
    """
    # Allow -foo or --foo.
    key_value_str = key_value_str.lstrip("-")
    key, _, value_str = key_value_str.partition("=")
    key = key.strip().replace("-", "_")
    value_str = value_str.strip()
    value = shell_unquote(value_str) if value_str else True

    return key, value


def parse_command_str(command_str: str) -> Tuple[str, List[str], Dict[str, str | bool]]:
    """
    Parse a command string into a command name, arguments, and options, using simplified
    shell conventions (compatible with Python and xonsh).

    Commands are expected to be formatted using shell conventions. Arguments and options
    can appear in any order.

    Strings are quoted using Python conventions. (Note this is not standard bash, so we do
    _not_ use shlex.split(). But it is compatible with xonsh.)

    Examples:

    command arg1 arg2 arg 3 --opt1=val1 --opt2=val2 --opt3
    command --opt1="val 1" --opt2 "arg 1" "arg 1" "arg 2"
    """

    tokens = shell_split(command_str)

    name = tokens[0]
    args = []
    options = {}
    for token in tokens[1:]:
        if token.startswith("-"):
            key, value = parse_option(token.lstrip("-"))
            options[key] = value
        else:
            arg = shell_unquote(token)
            args.append(arg)

    return name, args, options


@dataclass(frozen=True)
class ShellArgs:
    pos_args: List[str]
    kw_args: Dict[str, str | bool]
    show_help: bool = False


def parse_shell_args(args: List[str]) -> ShellArgs:
    """
    Parse pre-split shell input arguments into positional and keyword arguments,
    also handling boolean flags and help.

    ["foo", "--opt1", "--opt2='bar baz'"]
      -> ShellArgs(pos_args=["foo"], kw_args={"opt1": True, "opt2": "bar baz"}, show_help=False)

    ["foo", "--help"]
      -> ShellArgs(pos_args=["foo"], kw_args={}, show_help=True)
    """
    pos_args: List[str] = []
    kw_args: Dict[str, str | bool] = {}
    show_help: bool = False

    i = 0
    while i < len(args):
        if args[i].startswith("-"):
            key, value = parse_option(args[i])
            if key == "help":
                show_help = True
            else:
                kw_args[key] = value
            i += 1
        else:
            pos_args.append(args[i])
            i += 1

    return ShellArgs(pos_args=pos_args, kw_args=kw_args, show_help=show_help)


## Tests


def test_shell_split():
    assert shell_split("simple command") == ["simple", "command"]
    assert shell_split('quoted "string with spaces"') == ["quoted", '"string with spaces"']
    assert shell_split("""mixed 'single' and "double" quotes""") == [
        "mixed",
        "'single'",
        "and",
        '"double"',
        "quotes",
    ]
    assert shell_split(r"escaped \"quotes\" and spaces") == [
        r"escaped",
        r"\"quotes\"",
        "and",
        "spaces",
    ]
    assert shell_split("nested \"quotes 'inside' quotes\"") == [
        "nested",
        "\"quotes 'inside' quotes\"",
    ]
    assert shell_split('command with "quoted argument" and unquoted') == [
        "command",
        "with",
        '"quoted argument"',
        "and",
        "unquoted",
    ]
    assert shell_split("") == []
    assert shell_split(" \n  ") == []


def test_parse_and_format_command_str():
    # Test basic parsing and formatting.
    command_str = "mycommand arg1 arg2 --option1=value1 --flag"
    name, args, options = parse_command_str(command_str)
    assert name == "mycommand"
    assert args == ["arg1", "arg2"]
    assert options == {"option1": "value1", "flag": True}

    # Test roundtrip.
    reconstructed = format_command_str(name, args, options)
    assert reconstructed == command_str

    # Test with quoted arguments and option values.
    complex_command = 'complex "quoted arg" --option="quoted value" --flag "spaced arg"'
    name, args, options = parse_command_str(complex_command)
    assert name == "complex"
    assert args == ["quoted arg", "spaced arg"]
    assert options == {"option": "quoted value", "flag": True}

    # Test roundtrip with complex command.
    reconstructed = format_command_str(name, args, options)
    assert reconstructed == 'complex "quoted arg" "spaced arg" --option="quoted value" --flag'

    # Test with empty arguments and options.
    empty_command = "empty_cmd"
    name, args, options = parse_command_str(empty_command)
    assert name == "empty_cmd"
    assert args == []
    assert options == {}

    # Test roundtrip with empty command.
    reconstructed = format_command_str(name, args, options)
    assert reconstructed == empty_command


def test_parse_shell_args():
    args = [
        "pos1",
        "pos2",
        "--key1=value1",
        "--key2",
        "pos3",
        "-k3=value3",
        "--key4='two words'",
        "--help",
    ]
    shell_args = parse_shell_args(args)

    assert shell_args.pos_args == [
        "pos1",
        "pos2",
        "pos3",
    ]
    assert shell_args.kw_args == {
        "key1": "value1",
        "key2": True,
        "k3": "value3",
        "key4": "two words",
    }
    assert shell_args.show_help == True