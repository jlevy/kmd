from typing import Callable, Optional

from kmd.model.errors_model import PreconditionFailure
from kmd.model.items_model import Item


class Precondition:
    """
    A Precondition is a criterion that can be used to filter Items or qualify which
    Items may be inputs to given Actions. Function can return a bool or raise
    `PreconditionFailure`.

    Preconditions can be combined with `&`, `|`, and `~` operators.
    """

    def __init__(self, func: Callable[[Item], bool], name: Optional[str] = None):
        self.func = func
        self.name: str = name or func.__name__

    def check(self, item: Item, info: Optional[str] = None) -> None:
        info_str = f" for {info}" if info else ""
        if not self(item):
            raise PreconditionFailure(
                f"Precondition not satisfied{info_str}: {self} is false for {item.fmt_path_or_title()}"
            )

    def __call__(self, item: Item) -> bool:
        try:
            return self.func(item)
        except PreconditionFailure:
            return False

    def __and__(self, other: "Precondition") -> "Precondition":
        return Precondition(lambda item: self(item) and other(item), f"{self.name} & {other.name}")

    def __or__(self, other: "Precondition") -> "Precondition":
        return Precondition(lambda item: self(item) or other(item), f"{self.name} | {other.name}")

    def __invert__(self) -> "Precondition":
        return Precondition(lambda item: not self(item), f"~{self.name}")

    def __str__(self) -> str:
        return f"`{self.name}`"

    @staticmethod
    def and_all(*preconditions: "Precondition") -> "Precondition":
        if not preconditions:
            return Precondition(lambda item: True, "always")
        combined = preconditions[0]
        for precondition in preconditions[1:]:
            combined = combined & precondition
        return combined

    @staticmethod
    def or_all(*preconditions: "Precondition") -> "Precondition":
        if not preconditions:
            return Precondition(lambda item: False, "never")
        combined = preconditions[0]
        for precondition in preconditions[1:]:
            combined = combined | precondition
        return combined


def precondition(func: Callable[[Item], bool]) -> Precondition:
    """
    Decorator to make a function a Precondition. The function should return
    a bool and/or raise `PreconditionFailure`.
    """
    return Precondition(func)
