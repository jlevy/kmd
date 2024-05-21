from typing import NewType

from kmd.util.url import Url


# Mostly for readability and light type checking.
StorePath = NewType("StorePath", str)
Locator = Url | StorePath | str
