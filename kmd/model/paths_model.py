from pathlib import Path
from typing import cast, Type

from pydantic import constr, ValidationInfo

from kmd.errors import InvalidInput
from kmd.util.format_utils import fmt_path
from kmd.util.url import is_url, Url


def validate_relative_path(value: str) -> str:
    if not value or value.startswith("/") or Path(value).is_absolute():
        raise InvalidInput(f"Must be a relative path: {fmt_path(value)}")
    return value


RelativePath: Type[str] = constr(strip_whitespace=True)


class StorePath(RelativePath):
    """
    A relative path of an item in the file store.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str, info: ValidationInfo) -> str:
        return validate_relative_path(value)


Locator = Url | StorePath
"""
A reference to an external resource or an item in the store.
"""


InputArg = Locator | Path | str
"""
An argument to a command or action.
"""


def is_store_path(input_arg: InputArg) -> bool:
    if isinstance(input_arg, StorePath):
        return True
    elif isinstance(input_arg, Path):
        return False
    else:
        return not is_url(input_arg)


def as_url_or_path(input: str | Path) -> Path | Url:
    return cast(Url, str(input)) if is_url(str(input)) else cast(Path, input)
