import sys
from pathlib import Path, PosixPath, WindowsPath
from typing import cast

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from kmd.util.url import is_url, Url


# Determine the base class for StorePath based on the operating system
if sys.platform == "win32":
    BasePath = WindowsPath
else:
    BasePath = PosixPath


class StorePath(BasePath):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        if self.is_absolute():
            raise ValueError(f"Must be a relative path: {self}")
        return self

    def __truediv__(self, key):
        if isinstance(key, Path) and key.is_absolute():
            raise TypeError("Cannot join a StorePath with an absolute Path")
        result = super().__truediv__(key)
        return StorePath(result)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler):
        # Use the handler to get the schema for the base Path type
        path_schema = handler(BasePath)
        return core_schema.no_info_after_validator_function(
            cls.validate,
            path_schema,
        )

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return value
        try:
            # Attempt to create a StorePath instance
            return cls(value)
        except Exception as e:
            raise ValueError(f"Invalid StorePath: {value}") from e


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
