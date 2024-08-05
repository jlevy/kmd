from typing import NewType
from kmd.util.url import Url, is_url


# Mostly for readability and light type checking.
StorePath = NewType("StorePath", str)
Locator = Url | StorePath | str


def is_store_path(locator: Locator) -> bool:
    # TODO: Currently we assume args URLs or StorePaths but in the future they could be
    # other strings.
    return isinstance(locator, type(StorePath)) or not is_url(locator)
