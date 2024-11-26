import inspect
from functools import cache
from typing import List

from kmd.model.preconditions_model import Precondition


@cache
def all_preconditions() -> List[Precondition]:
    import kmd.preconditions.precondition_defs as precondition_defs

    return [
        value
        for _name, value in inspect.getmembers(precondition_defs)
        if isinstance(value, Precondition)
    ]
