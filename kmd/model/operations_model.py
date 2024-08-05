from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from kmd.model.locators import StorePath
from kmd.util.log_calls import quote_if_needed


@dataclass(frozen=True)
class OperationSummary:
    """
    Summary of an operation (action and all arguments) that was performed on an item. We could include
    all arguments, hashes, etc for every operation but that seems like a cumbersome amount of metadata,
    so just keeping a brief summary.
    """

    operation: str


@dataclass(frozen=True)
class Input:
    """
    An input to an operation, which may include a hash fingerprint.
    """

    # TODO: May want to support Locators or other inputs besides StorePaths.
    path: StorePath
    hash: Optional[str] = None

    def path_and_hash(self):
        return f"{self.path}@{self.hash}"

    def __str__(self):
        return self.path_and_hash()

    @classmethod
    def parse(cls, input_str: str) -> "Input":
        """
        Parse an Input string in the format `path@hash`.
        """
        parts = input_str.split("@")
        if len(parts) > 2:
            raise ValueError(
                f"Invalid input string format. Expected 'path@hash' or 'path': {input_str}"
            )
        elif len(parts) == 2:
            path, hash = parts
            return cls(path=StorePath(path), hash=hash)
        else:
            return cls(path=StorePath(input_str), hash=None)


@dataclass(frozen=True)
class Operation:
    """
    A single operation that was performed. An operation is an action together with all the
    inputs to that action.
    """

    operation: str
    arguments: List[Input]

    def summary(self) -> OperationSummary:
        return OperationSummary(self.operation)

    def command_line(self):
        quoted_args = [quote_if_needed(str(arg.path)) for arg in self.arguments]
        return f"{self.operation} {' '.join(quoted_args)}"

    def as_dict(self):
        return {
            "operation": self.operation,
            "arguments": [arg.path_and_hash() for arg in self.arguments],
        }

    def paths_eq(self, other: "Operation") -> bool:
        return (
            self.operation == other.operation
            and len(self.arguments) == len(other.arguments)
            and all(a.path == b.path for a, b in zip(self.arguments, other.arguments))
        )

    def exact_eq(self, other: "Operation") -> bool:
        return self.paths_eq(other) and all(
            a.hash == b.hash for a, b in zip(self.arguments, other.arguments)
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Operation):
            return NotImplemented
        return self.exact_eq(other)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Operation":
        operation = d["operation"]
        arguments = [Input.parse(input_str) for input_str in d.get("arguments", [])]
        return cls(operation=operation, arguments=arguments)

    def __str__(self):
        return self.command_line()


# Just a nicety to help with sorting these keys when serializing to YAML.
OPERATION_FIELDS = ["operation", "arguments"]
