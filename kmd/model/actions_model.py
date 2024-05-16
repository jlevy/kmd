from abc import abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from kmd.model.items_model import Item


@dataclass
class ExpectedArgs:
    min_args: Optional[int]
    max_args: Optional[int]


ONE_ARG = ExpectedArgs(1, 1)
NO_ARGS = ExpectedArgs(0, 0)
ANY_ARGS = ExpectedArgs(0, None)

# For now these are simple but we will want to support other hints or output data in the future.
ActionInput = List[Item]


@dataclass
class ActionResult:
    items: List[Item]

    # If True, a hint to archive the input items.
    replaces_input: bool = False


@dataclass
class Action:
    name: str
    friendly_name: str
    description: str
    implementation: str = "builtin"
    model: Optional[str] = None
    title_template: Optional[str] = None
    template: Optional[str] = None
    system_message: Optional[str] = None
    expected_args: ExpectedArgs = field(default_factory=lambda: ONE_ARG)

    def validate_args(self, args: List[str]) -> None:
        if len(args) != 0 and self.expected_args == NO_ARGS:
            raise ValueError(f"Action {self.name} does not expect any arguments")
        if len(args) != 1 and self.expected_args == ONE_ARG:
            raise ValueError(f"Action {self.name} expects exactly one argument")
        if self.expected_args.max_args is not None and len(args) > self.expected_args.max_args:
            raise ValueError(
                f"Action {self.name} expects at most {self.expected_args.max_args} arguments"
            )
        if self.expected_args.min_args is not None and len(args) < self.expected_args.min_args:
            raise ValueError(
                f"Action {self.name} expects at least {self.expected_args.min_args} arguments"
            )

    @abstractmethod
    def run(self, items: ActionInput) -> ActionResult:
        pass
