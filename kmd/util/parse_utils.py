import ast
from enum import Enum
import shlex
from typing import Any, Optional, Tuple, Type, TypeVar
from kmd.util.type_utils import instantiate_as_type


def parse_shell_str(s: str) -> str:
    s = s.strip()
    return shlex.split(s)[0]


def format_shell_str(s: Any) -> str:
    return shlex.quote(str(s))


def parse_python_str(s: str) -> str:
    s = s.strip()
    if s.startswith(("'", '"')) and s.endswith(("'", '"')):
        return ast.literal_eval(s)
    else:
        return ast.literal_eval(f'"{s}"')


def format_python_str_or_enum(s: Any) -> str:
    if isinstance(s, Enum):
        return s.value
    return repr(s)


T = TypeVar("T")


def parse_key_value(
    key_value_str: str, value_parser=parse_python_str, target_type: Type[T] = str
) -> Tuple[str, Optional[T]]:
    """
    Parse a key-alue string like `foo=123` or `bar="some value"` into a `(key, value)` tuple.
    A string like `foo=` (with only whitespace after the `=`) will yield `("foo", None)`.
    """
    key, _, value = key_value_str.partition("=")
    if not value.strip():
        value = None
    else:
        # Handle quoted values.
        value = value_parser(value)
    key = key.strip()

    value = instantiate_as_type(value, target_type)

    return key, value


def format_key_value(key: str, value: Any, value_formatter=format_shell_str) -> str:
    """
    Format a key-value pair as a string like `foo=123` or `bar='some value'`.
    """

    def value_str(value: Any) -> str:
        return "" if value is None else value_formatter(value)

    return f"{key}={value_str(value)}"


## Tests


def test_key_value_parsing_and_formatting():
    assert parse_key_value("foo=123") == ("foo", "123")
    assert parse_key_value(" foo='123'") == ("foo", "123")
    assert parse_key_value('bar="some value"') == ("bar", "some value")
    assert parse_key_value("bar = 'some value'") == ("bar", "some value")
    assert parse_key_value("foo=") == ("foo", None)

    assert format_key_value("foo", "123") == "foo=123"
    assert format_key_value("bar", "some value") == "bar='some value'"
    assert format_key_value("foo", None) == "foo="
    assert format_key_value("foo", "") == "foo=''"
