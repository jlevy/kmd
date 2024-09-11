from abc import ABC, abstractmethod
from copy import copy
from dataclasses import dataclass, fields
from enum import Enum
from typing import Any, cast, Dict, List, Optional, Sequence, TYPE_CHECKING

from kmd.config.logger import get_logger
from kmd.lang_tools.inflection import plural
from kmd.model.arguments_model import InputArg, StorePath
from kmd.model.errors_model import InvalidInput, NONFATAL_EXCEPTIONS
from kmd.model.items_model import Item, ItemType, UNTITLED
from kmd.model.language_models import LLM
from kmd.model.messages_model import Message, MessageTemplate
from kmd.model.operations_model import Operation, Source
from kmd.model.params_model import ALL_COMMON_PARAMS, Param, ParamValues, TextUnit
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_defs import is_text_doc
from kmd.text_docs.sliding_transforms import WindowSettings
from kmd.text_docs.text_diffs import DiffFilterType
from kmd.text_formatting.text_formatting import fmt_lines
from kmd.text_ui.command_output import fill_text
from kmd.util.obj_utils import abbreviate_obj
from kmd.util.parse_utils import format_key_value
from kmd.util.string_template import StringTemplate
from kmd.util.task_stack import task_stack
from kmd.util.type_utils import instantiate_as_type

if TYPE_CHECKING:
    from kmd.model.output_model import CommandOutput

log = get_logger(__name__)


@dataclass(frozen=True)
class ExpectedArgs:
    min_args: Optional[int]
    max_args: Optional[int]


ANY_ARGS = ExpectedArgs(0, None)
NO_ARGS = ExpectedArgs(0, 0)
ONE_OR_NO_ARGS = ExpectedArgs(0, 1)
ONE_OR_MORE_ARGS = ExpectedArgs(1, None)
ONE_ARG = ExpectedArgs(1, 1)
TWO_OR_MORE_ARGS = ExpectedArgs(2, None)
TWO_ARGS = ExpectedArgs(2, 2)


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

    command_output: Optional["CommandOutput"] = None
    """If specified, control the output from the command."""

    def __str__(self):
        return abbreviate_obj(self, field_max_len=80)


@dataclass(frozen=True)
class Action(ABC):
    """
    The base classes for Actions, which are arbitrary operations that can be
    performed on Items. Instantiate this or a more specific subclass to create
    an action.
    """

    name: str
    """The name of the action. Should be in lower_snake_case."""

    description: str
    """A description of the action, in a few sentences."""

    precondition: Optional[Precondition] = None
    """Mainly a sanity check. For simplicity we apply one precondition on all args."""

    expected_args: ExpectedArgs = ONE_ARG
    """The required number of arguments. We use exactly one by default to make it easy to wrap in a ForEachItemAction."""

    interactive_input: bool = False
    """Does this action ask for input interactively?"""

    # These are set if they make sense, i.e. it's an LLM action.
    model: Optional[LLM] = None
    language: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_unit: Optional[TextUnit] = None
    title_template: Optional[TitleTemplate] = None
    template: Optional[MessageTemplate] = None
    system_message: Optional[Message] = None

    _NON_PARAM_FIELDS = [
        "name",
        "description",
        "precondition",
        "expected_args",
        "interactive_input",
    ]

    # Long fields we don't want to include in the summary.
    _NON_SUMMARY_FIELDS = [
        "title_template",
        "template",
        "system_message",
        "windowing",
    ]

    def __post_init__(self):
        # Class is frozen but we do want to update the description.
        object.__setattr__(self, "description", fill_text(self.description))

    def validate_args(self, args: Sequence[InputArg]) -> None:
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
                self.precondition.check(item, self.name)

    def param_names(self) -> List[str]:
        return sorted(
            set(f.name for f in fields(self) if not f.name.startswith("_"))
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

        summary_param_names = sorted(
            set(f.name for f in fields(self) if not f.name.startswith("_"))
            - set(self._NON_PARAM_FIELDS)
            - set(self._NON_SUMMARY_FIELDS)
        )
        changed_params: Dict[str, Any] = {}
        for param_name in summary_param_names:
            value = getattr(self, param_name)
            if value:
                changed_params[param_name] = stringify(value)
        return changed_params

    def param_summary_str(self) -> str:
        summary_str = fmt_lines(
            [format_key_value(name, value) for name, value in self.param_summary().items()]
        )
        return f"Action params:\n{summary_str}"

    def update_with_params(self, param_values: ParamValues, strict: bool = False) -> "Action":
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
                        "Unknown override param for action `%s`: %s", self.name, param_name
                    )
                else:
                    log.warning(
                        "Ignoring unknown override param for action `%s`: %s", self.name, param_name
                    )
                    continue

            # Convert value to the appropriate type.
            if param_name in action_param_names:
                field_info = next(f for f in fields(self) if f.name == param_name)
                value = instantiate_as_type(value, cast(type, field_info.type))

            # Update the action.
            if param_name in ALL_COMMON_PARAMS and param_name in action_param_names:
                # Use object.__setattr__ to update the frozen instance.
                object.__setattr__(new_instance, param_name, value)
                overrides.append(format_key_value(param_name, value))

        if overrides:
            log.message(
                "Overriding parameters for action `%s`:\n%s",
                self.name,
                fmt_lines(overrides),
            )

        return new_instance

    def preassemble_one(
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

        Default behavior is to return None, which means this is disabled.
        """
        return None

    @abstractmethod
    def run(self, items: ActionInput) -> ActionResult:
        pass

    def __str__(self):
        return abbreviate_obj(self)


@dataclass(frozen=True)
class ForEachItemAction(Action):
    """
    Abstract base action that simply processes each arg one after the other. If "non fatal"
    errors are encountered, they are reported and processing continues with the next item.
    """

    expected_args: ExpectedArgs = ONE_OR_MORE_ARGS

    def run(self, items: ActionInput) -> ActionResult:

        with task_stack().context(self.name, len(items), "item") as ts:
            result_items: List[Item] = []
            errors: List[Exception] = []
            multiple_inputs = len(items) > 1

            for i, item in enumerate(items):

                log.message(
                    "Action `%s` input item %d/%d:\n%s",
                    self.name,
                    i + 1,
                    len(items),
                    fmt_lines([item]),
                )
                had_error = False
                try:
                    result_item = self.run_item(item)
                    result_items.append(result_item)
                    had_error = False
                except NONFATAL_EXCEPTIONS as e:
                    errors.append(e)
                    had_error = True

                    if multiple_inputs:
                        log.error(
                            "Error processing item; continuing with others: %s: %s",
                            e,
                            item,
                        )
                    else:
                        # If there's only one input, fail fast.
                        raise e
                finally:
                    ts.next(last_had_error=had_error)

            if errors:
                log.error(
                    "%s %s occurred while processing items. See above!",
                    len(errors),
                    plural("error", len(errors)),
                )

        return ActionResult(result_items)

    @abstractmethod
    def run_item(self, item: Item) -> Item:
        pass


@dataclass(frozen=True)
class CachedDocAction(ForEachItemAction):
    """
    Abstract base action that simply processes each input and returns a single doc output for each.
    The output title etc. are derived from the first input item. Caches and skips items that have
    already been processed.
    """

    # Implementing this makes caching work.
    def preassemble(self, operation: Operation, items: ActionInput) -> Optional[ActionResult]:
        return ActionResult(
            [self.preassemble_one(operation, items, output_num=0, type=ItemType.doc)]
        )


@dataclass(frozen=True)
class TransformAction(Action):
    """
    Abstract base for actions with windowed transforms.
    """

    expected_args: ExpectedArgs = ONE_OR_MORE_ARGS
    precondition: Optional[Precondition] = is_text_doc

    windowing: Optional[WindowSettings] = None
    diff_filter: Optional[DiffFilterType] = None

    @abstractmethod
    def run(self, items: ActionInput) -> ActionResult:
        pass
