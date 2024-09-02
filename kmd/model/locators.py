from pathlib import Path
from typing import Self
from kmd.model.errors_model import InvalidInput
from kmd.text_formatting.text_formatting import fmt_path
from kmd.util.url import Url, is_url


class StorePath(str):
    """
    A relative path of an item in the file store. This can be used interchangably with
    str but helps with readability, easy casting from Path, and light type checking.
    """

    def __new__(cls, path: str | Path) -> Self:
        if not path or str(path).startswith("/") or Path(path).is_absolute():
            raise InvalidInput(f"StorePath must be a relative path: {fmt_path(path)}")

        return super().__new__(cls, str(path))


Locator = Url | StorePath | str


def is_store_path(locator: Locator) -> bool:
    # TODO: Currently we assume args URLs or StorePaths but in the future they could be
    # other strings.
    return isinstance(locator, type(StorePath)) or not is_url(locator)
