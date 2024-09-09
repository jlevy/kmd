import inspect

import kmd.preconditions.precondition_defs as precondition_defs
from kmd.model.preconditions_model import Precondition


ALL_PRECONDITIONS = [
    value
    for _name, value in inspect.getmembers(precondition_defs)
    if isinstance(value, Precondition)
]
