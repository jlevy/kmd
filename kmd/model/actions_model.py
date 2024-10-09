from abc import ABC, abstractmethod
from copy import copy
from dataclasses import Field
from enum import Enum
from typing import Any, cast, ClassVar, Dict, Iterable, List, Optional, Sequence

from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.model.items_model import Item, ItemType, UNTITLED
from kmd.model.language_models import LLM
from kmd.model.messages_model import Message, MessageTemplate
from kmd.model.operations_model import Operation, Source
from kmd.model.output_model import CommandOutput
from kmd.model.params_model import ALL_COMMON_PARAMS, Param, ParamValues, TextUnit
from kmd.model.paths_model import InputArg, StorePath
from kmd.model.preconditions_model import Precondition
from kmd.text_docs.diff_filters import DiffFilter
from kmd.text_docs.window_settings import WindowSettings
from kmd.text_ui.command_output import fill_text
from kmd.util.format_utils import fmt_lines
from kmd.util.obj_utils import abbreviate_obj
from kmd.util.parse_utils import format_key_value
from kmd.util.string_template import StringTemplate
from kmd.util.type_utils import instantiate_as_type

log = get_logger(__name__)


@dataclass(frozen=True)
class ArgCount:
    min_args: Optional[int]
    max_args: Optional[int]


ANY_ARGS = ArgCount(0, None)
NO_ARGS = ArgCount(0, 0)
ONE_OR_NO_ARGS = ArgCount(0, 1)
ONE_OR_MORE_ARGS = ArgCount(1, None)
ONE_ARG = ArgCount(1, 1)
TWO_OR_MORE_ARGS = ArgCount(2, None)
TWO_ARGS = ArgCount(2, 2)


class TitleTemplate(StringTemplate):
    """A template for a title."""

    def __init__(self, template: str):
        super().__init__(template.strip(), allowed_fields=["title", "action_name"])


# For now these are simple but we will want to support other hints or output data in the future.
ActionInput = List[Item]


class PathOpType(Enum):
    archive = "archive"
    select = "select"


@dataclass(frozen=True)
class PathOp:
    """
    An operation on a path.
    """

    store_path: StorePath
    op: PathOpType


@dataclass
class ActionResult:
    items: List[Item]
    """Results from this action. Most often, just a single item."""

    replaces_input: bool = False
    """If True, a hint to archive the input items."""

    skip_duplicates: bool = False
    """If True, do not save duplicate items (based on identity)."""

    path_ops: Optional[List[PathOp]] = None
    """If specified, operations to perform on specific paths, such as selecting items."""

    command_output: Optional[CommandOutput] = None
    """If specified, control the output from the command."""

    def has_hints(self) -> bool:
        return bool(
            self.replaces_input or self.skip_duplicates or self.path_ops or self.command_output
        )

    def __str__(self):
        return abbreviate_obj(self, field_max_len=80)


@dataclass
class ExecContext:
    """
    Context for an action's execution.
    """

    action: "Action"
    """The action being executed."""


@dataclass
class Action(ABC):
    """
    The base class for Actions, which are arbitrary operations that can be
    performed on Items. Instantiate this or a more specific subclass to create
    an action.
    """

    name: str
    """The name of the action. Should be in lower_snake_case."""

    description: str
    """A description of the action, in a few sentences."""

    cachable: bool = True
    """
    If True, the action execution may be skipped if the output is already present.
    """

    precondition: Optional[Precondition] = None
    """Mainly a sanity check. For simplicity, the precondition must apply to all args."""

    expected_args: ArgCount = ONE_ARG
    """The required number of arguments. We use exactly one by default to make it easy to wrap in a ForEachItemAction."""

    output_type: ItemType = ItemType.doc
    """The type of the output item(s)."""

    expected_outputs: ArgCount = ONE_ARG
    """The number of outputs expected from this action."""

    run_per_item: bool = False
    """
    Normally, an action runs on all input items at once. If True, run the action separately
    for each input item, each time on a single item.
    """

    interactive_input: bool = False
    """Does this action ask for input interactively?"""

    # More specific options that apply only to certain types of actions below.
    # TODO: Might want to move these into an ActionParams class for clarity.

    # Transform-specific options:
    windowing: Optional[WindowSettings] = None
    diff_filter: Optional[DiffFilter] = None

    # LLM-specific options:
    model: Optional[LLM] = None
    language: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_unit: Optional[TextUnit] = None
    title_template: Optional[TitleTemplate] = None
    template: Optional[MessageTemplate] = None
    system_message: Optional[Message] = None

    _NON_PARAM_FIELDS: ClassVar[List[str]] = [
        "name",
        "description",
        "precondition",
        "expected_args",
        "interactive_input",
    ]

    # Long or obvious fields we don't want to include in the summary.
    _NON_SUMMARY_FIELDS: ClassVar[List[str]] = [
        "title_template",
        "template",
        "system_message",
        "windowing",
        "expected_outputs",
        "output_type",
    ]

    def __post_init__(self):
        self.description = fill_text(self.description)
        if self.run_per_item:
            self.expected_args = ONE_ARG
        self.validate_sanity()

    def validate_sanity(self):
        if self.run_per_item and self.expected_args != ONE_ARG:
            raise InvalidInput(
                f"Action `{self.name}` has run_per_item=True but does not expect a single argument: {self.expected_args}"
            )

    def validate_args(self, args: Sequence[InputArg]) -> None:
        self.validate_sanity()

        if self.run_per_item:
            if len(args) < 1:
                log.warning("Running action `%s` for each input but got no inputs", self.name)
            return

        nargs = len(args)
        if nargs != 0 and self.expected_args == NO_ARGS:
            raise InvalidInput(f"Action `{self.name}` does not expect any arguments")
        if nargs != 1 and self.expected_args == ONE_ARG:
            raise InvalidInput(f"Action `{self.name}` expects exactly one argument")
        if self.expected_args.max_args is not None and nargs > self.expected_args.max_args:
            raise InvalidInput(
                f"Action `{self.name}` expects at most {self.expected_args.max_args} arguments"
            )
        if self.expected_args.min_args is not None and nargs < self.expected_args.min_args:
            raise InvalidInput(
                f"Action `{self.name}` expects at least {self.expected_args.min_args} arguments"
            )

    def validate_precondition(self, items: ActionInput) -> None:
        if self.precondition:
            for item in items:
                self.precondition.check(item, f"action `{self.name}`")

    def param_names(self) -> List[str]:
        fields: Iterable[Field] = self.__dataclass_fields__.values()
        return sorted(
            set([f.name for f in fields if not f.name.startswith("_")])
            - set(self._NON_PARAM_FIELDS)
        )

    def params(self) -> List[Param]:
        return [ALL_COMMON_PARAMS.get(name) or Param(name, type=str) for name in self.param_names()]

    def param_summary(self) -> Dict[str, str]:
        """
        Readable, serializable summary of the action's non-default parameters.
        """

        def stringify(value: Any) -> str:
            if isinstance(value, Enum):
                return value.name
            return str(value)

        summary_param_names = sorted(set(self.param_names()) - set(self._NON_SUMMARY_FIELDS))

        changed_params: Dict[str, Any] = {}
        for param_name in summary_param_names:
            if hasattr(self, param_name):
                value = getattr(self, param_name)
                if value:
                    changed_params[param_name] = stringify(value)
        return changed_params

    def param_summary_str(self) -> str:
        summary_str = fmt_lines(
            [format_key_value(name, value) for name, value in self.param_summary().items()]
        )
        return f"Parameters:\n{summary_str}"

    def with_params(self, param_values: ParamValues, strict: bool = False) -> "Action":
        """
        Update the action with the given parameters and return a new Action.
        """
        new_instance = copy(self)  # Shallow copy.
        action_param_names = self.param_names()

        overrides = []
        for param_name, value in param_values.items():
            # Sanity checks.
            if param_name not in ALL_COMMON_PARAMS and param_name not in action_param_names:
                if strict:
                    raise InvalidInput(
                        f"Unknown override param for action `{self.name}`: {param_name}"
                    )
                else:
                    log.warning(
                        "Ignoring unknown override param for action `%s`: %s", self.name, param_name
                    )
                    continue

            # Convert value to the appropriate type.
            if param_name in action_param_names:
                field_info: Field = next(
                    f for f in self.__dataclass_fields__.values() if f.name == param_name
                )
                value = instantiate_as_type(value, cast(type, field_info.type))

            # Update the action.
            if param_name in ALL_COMMON_PARAMS and param_name in action_param_names:
                setattr(new_instance, param_name, value)
                overrides.append(format_key_value(param_name, value))

        if overrides:
            log.message(
                "Overriding parameters for action `%s`:\n%s",
                self.name,
                fmt_lines(overrides),
            )

        return new_instance

    def _preassemble_one(
        self,
        operation: Operation,
        items: ActionInput,
        output_num: int,
        type: ItemType,
        **kwargs,
    ) -> Item:
        """
        Preassemble a single empty output item from the given input items. Include the title,
        type, and last Operation so we can do an identity check if the output already exists.
        """
        primary_input = items[output_num]
        item = primary_input.derived_copy(type=type, body=None, **kwargs)

        if self.title_template:
            item.title = self.title_template.format(title=primary_input.title or UNTITLED)

        item.update_history(Source(operation=operation, output_num=output_num))

        return item

    def preassemble(self, operation: Operation, items: ActionInput) -> Optional[ActionResult]:
        """
        Actions can have a separate preliminary step to pre-assemble outputs. This allows us to
        determine the title and types for the output items and check if they were already
        generated before running slow or expensive actions.

        For now, this only applies to actions with a single output, if self.cachable is True.
        """
        log.info(
            "Preassemble check for `%s` is %s (%s with cachable=%s)",
            self.name,
            self.cachable and self.expected_outputs == ONE_ARG,
            self.expected_outputs,
            self.cachable,
        )
        if self.cachable and self.expected_outputs == ONE_ARG:
            return ActionResult(
                [self._preassemble_one(operation, items, output_num=0, type=self.output_type)]
            )
        else:
            # Caching disabled.
            return None

    def context(self) -> ExecContext:
        return ExecContext(action=self)

    @abstractmethod
    def run(self, items: ActionInput) -> ActionResult:
        pass

    def __str__(self):
        return abbreviate_obj(self)


@dataclass
class PerItemAction(Action):
    """
    Abstract base class for an action that processes one input item and returns
    one output item.

    Note that this action can be invoked on many input items, but the run method
    itself must expect exactly one input item and the executor will run it for each
    input.
    """

    expected_args: ArgCount = ONE_ARG
    run_per_item: bool = True

    def run(self, items: ActionInput) -> ActionResult:
        log.info("Running action `%s` per-item.", self.name)
        return ActionResult(items=[self.run_item(items[0])])

    @abstractmethod
    def run_item(self, item: Item) -> Item:
        pass
