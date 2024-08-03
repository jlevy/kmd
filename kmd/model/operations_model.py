from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class OperationSummary:
    """
    Summary of an operation (action and all arguments) that was performed on an item. We could include
    all arguments, hashes, etc for every operation but that seems like a cumbersome amount of metadata,
    so just keeping a brief summary.
    """

    operation: str


def quote_if_needed(arg: str) -> str:
    """
    Quoting compatible with most shells and xonsh.
    """
    if " " in arg or "'" in arg or '"' in arg:
        return repr(arg)
    return arg


@dataclass(frozen=True)
class Operation:
    """
    A single operation that was performed. An operation is an action together with all the
    inputs to that action.
    """

    operation: str
    arguments: List[str]

    def summary(self) -> OperationSummary:
        return OperationSummary(self.operation)

    def command_line(self):
        quoted_args = [quote_if_needed(arg) for arg in self.arguments]
        return f"{self.operation} {' '.join(quoted_args)}"

    def __str__(self):
        return self.command_line()


# Just a nicety to help with sorting these keys when serializing to YAML.
OPERATION_FIELDS = ["operation", "arguments"]
