import inspect
from typing import List

from cachetools import cached

from kmd.model.preconditions_model import Precondition


@cached({})
def all_preconditions() -> List[Precondition]:
    import kmd.preconditions.precondition_defs as precondition_defs

    return [
        value
        for _name, value in inspect.getmembers(precondition_defs)
        if isinstance(value, Precondition)
    ]
