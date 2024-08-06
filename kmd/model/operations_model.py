from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from kmd.model.locators import StorePath
from kmd.util.log_calls import quote_if_needed


@dataclass(frozen=True)
class OperationSummary:
    """
    Brief version of an operation that was performed on an item. We could include a history
    of the full Operations but that seems like a cumbersome amount of metadata, so just
    keeping a brief summary.
    """

    action_name: str


@dataclass(frozen=True)
class Input:
    """
    An input to an operation, which may include a hash fingerprint.
    """

    # TODO: May want to support Locators or other inputs besides StorePaths.
    path: StorePath
    hash: Optional[str] = None

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

    def path_and_hash(self):
        return f"{self.path}@{self.hash}"

    def __str__(self):
        return self.path_and_hash()


@dataclass(frozen=True)
class Operation:
    """
    A single operation that was performed. An operation is an action together with all the
    inputs to that action.
    """

    action_name: str
    arguments: List[Input]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Operation":
        action_name = d["action_name"]
        arguments = [Input.parse(input_str) for input_str in d.get("arguments", [])]
        return cls(action_name=action_name, arguments=arguments)

    def as_dict(self):
        return {
            "action_name": self.action_name,
            "arguments": [arg.path_and_hash() for arg in self.arguments],
        }

    def summary(self) -> OperationSummary:
        return OperationSummary(self.action_name)

    def command_line(self):
        quoted_args = [quote_if_needed(str(arg.path)) for arg in self.arguments]
        return f"{self.action_name} {' '.join(quoted_args)}"

    def paths_eq(self, other: "Operation") -> bool:
        return (
            self.action_name == other.action_name
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

    def as_str(self):
        return (
            self.action_name
            + "("
            + ", ".join(input.path_and_hash() for input in self.arguments)
            + ")"
        )

    def __str__(self):
        return self.as_str()


# Just a nicety to help with sorting these keys when serializing to YAML.
OPERATION_FIELDS = ["action_name", "arguments"]


@dataclass(frozen=True)
class Source:
    operation: Operation
    output_num: int

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Source":
        return cls(
            operation=Operation.from_dict(d["operation"]),
            output_num=d["output_num"],
        )

    def as_dict(self):
        return {
            "operation": self.operation.as_dict(),
            "output_num": self.output_num,
        }

    def as_str(self):
        return f"{self.operation.as_str()}[{self.output_num}]"

    def __str__(self):
        return self.as_str()
