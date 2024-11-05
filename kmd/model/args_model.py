from pathlib import Path
from typing import Optional

from pydantic.dataclasses import dataclass

from kmd.model.paths_model import StorePath
from kmd.util.format_utils import fmt_path
from kmd.util.url import is_url, Url

Locator = Url | Path | StorePath
"""
A reference to an external resource or an item in the store.
The resolved form of the most common type of input argument to commands and actions.
"""

InputArg = Locator | str
"""
An argument to a command or action. May include other strings that are not Locators.
"""


@dataclass(frozen=True)
class ArgCount:
    """
    The number of arguments required for a command or action.
    """

    min_args: Optional[int]
    max_args: Optional[int]


ANY_ARGS = ArgCount(0, None)
NO_ARGS = ArgCount(0, 0)
ONE_OR_NO_ARGS = ArgCount(0, 1)
ONE_OR_MORE_ARGS = ArgCount(1, None)
ONE_ARG = ArgCount(1, 1)
TWO_OR_MORE_ARGS = ArgCount(2, None)
TWO_ARGS = ArgCount(2, 2)


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


def is_store_path(input_arg: InputArg) -> bool:
    if isinstance(input_arg, StorePath):
        return True
    elif isinstance(input_arg, Path):
        return False
    else:
        return not is_url(input_arg)
