from pathlib import Path
from typing import Self

from kmd.model.errors_model import InvalidInput
from kmd.text_formatting.text_formatting import fmt_path
from kmd.util.url import is_url, Url


class StorePath(str):
    """
    A relative path of an item in the file store. This can be used as a str but
    helps with readability, easy casting from Path, and light type checking.
    """

    def __new__(cls, path: str | Path) -> Self:
        if not path or str(path).startswith("/") or Path(path).is_absolute():
            raise InvalidInput(f"StorePath must be a relative path: {fmt_path(path)}")

        return super().__new__(cls, str(path))


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
