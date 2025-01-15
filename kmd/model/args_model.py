from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic.dataclasses import dataclass

from kmd.lang_tools.inflection import plural
from kmd.model.paths_model import StorePath
from kmd.util.format_utils import fmt_path
from kmd.util.url import is_url, Url


Locator = Url | Path | StorePath
"""
A reference to an external resource or an item in the store.
The resolved form of the most common type of input argument to commands and actions.
"""

UnresolvedLocator = str | Locator


CommandArg = Locator | str
"""
An argument to a command or action. Will be formatted as a string but
may represent a string value, URL, path, store path, etc.
"""


class ArgType(Enum):
    """
    The type of an argument.
    """

    Path = "Path"
    StorePath = "StorePath"
    Url = "Url"
    Locator = "Locator"
    str = "str"


@dataclass(frozen=True)
class ArgCount:
    """
    The number of arguments required for a command or action.
    """

    min_args: Optional[int]
    max_args: Optional[int]

    def as_str(self) -> str:
        if self == ArgCount(0, 0):
            return "No arguments"
        elif self.min_args == self.max_args:
            return f"Exactly {self.min_args} {plural('argument', self.min_args)}"
        elif self.max_args is None:
            return f"{self.min_args} or more {plural('argument', self.min_args)}"
        else:
            return f"{self.min_args} to {self.max_args} {plural('argument', self.max_args)}"


ANY_ARGS = ArgCount(0, None)
NO_ARGS = ArgCount(0, 0)
ONE_OR_NO_ARGS = ArgCount(0, 1)
ONE_OR_MORE_ARGS = ArgCount(1, None)
ONE_ARG = ArgCount(1, 1)
TWO_OR_MORE_ARGS = ArgCount(2, None)
TWO_ARGS = ArgCount(2, 2)


@dataclass(frozen=True)
class Signature:
    """
    The signature (list of argument types) of a command or action.
    """

    arg_type: ArgType | List[ArgType]
    arg_count: ArgCount

    @classmethod
    def single_type(cls, arg_type: ArgType, arg_count: ArgCount) -> "Signature":
        return cls(arg_type, arg_count)

    @classmethod
    def multi_type(cls, arg_types: List[ArgType]) -> "Signature":
        nargs = len(arg_types)
        return cls(arg_types, ArgCount(nargs, nargs)).validate()

    def validate(self) -> "Signature":
        if self.arg_count.min_args != self.arg_count.max_args:
            raise ValueError(f"Multi-type argument count must be fixed: {self.arg_count}")
        if isinstance(self.arg_type, list) and len(self.arg_type) != self.arg_count.min_args:
            raise ValueError(
                f"Multi-type argument count must match number of types: {self.arg_count}"
            )
        return self

    def type_str(self) -> str:
        if isinstance(self.arg_type, list):
            return ", ".join(t.value for t in self.arg_type)
        else:
            return self.arg_type.value

    def human_str(self) -> str:
        return f"{self.arg_count.as_str()} of type {self.type_str()}"


def is_store_path(input_arg: CommandArg) -> bool:
    if isinstance(input_arg, StorePath):
        return True
    elif isinstance(input_arg, Path):
        return False
    else:
        return not is_url(input_arg)


def fmt_loc(locator: str | Locator) -> str:
    """
    Use this to format URLs and paths. This automatically formats StorePaths
    with an @ prefix, other Paths with quotes and relative to the working directory.
    It handles everything else like a string. (Note for code not involving
    StorePaths, you can use `fmt_path` directly for plain Paths.)
    """
    if isinstance(locator, StorePath):
        return locator.display_str()
    elif isinstance(locator, Path):
        return fmt_path(locator)
    elif is_url(loc_str := str(locator)):
        return loc_str
    else:
        return fmt_path(locator)
