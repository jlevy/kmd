from kmd.model.errors_model import PreconditionFailure
from kmd.model.items_model import Item


class Precondition:
    """
    A Precondition is a criterion that can be used to filter Items or qualify which
    Items may be inputs to given Actions. Function can return a bool or raise
    `PreconditionFailure`.
    """

    def __init__(self, func):
        self.func = func

    def check(self, item: Item) -> None:
        if not self(item):
            raise PreconditionFailure(f"Precondition not satisfied: {self}: {item}")

    def __call__(self, item: Item) -> bool:
        try:
            return self.func(item)
        except PreconditionFailure:
            return False

    def __and__(self, other: "Precondition") -> "Precondition":
        return Precondition(lambda item: self(item) and other(item))

    def __or__(self, other: "Precondition") -> "Precondition":
        return Precondition(lambda item: self(item) or other(item))

    def __invert__(self) -> "Precondition":
        return Precondition(lambda item: not self(item))


def precondition(func):
    """
    Decorator to make a function a Precondition. The function should return
    a bool and/or raise `PreconditionFailure`.
    """
    return Precondition(func)
