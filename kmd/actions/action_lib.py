from typing import List
from kmd.model.model import Item


# For now these are simple but we may want to support other hints or output data in the future.
ActionInput = List[Item]
ActionResult = List[Item]
