from abc import ABC, abstractmethod
from copy import copy
from dataclasses import Field as DataclassField
from enum import Enum
from typing import Any, cast, Dict, List, Optional, Sequence, TypeVar

from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.errors import InvalidActionDefinition, InvalidInput
from kmd.model.args_model import ArgCount, ArgType, CommandArg, NO_ARGS, ONE_ARG, Signature
from kmd.model.items_model import Item, ItemType, UNTITLED
from kmd.model.messages_model import Message, MessageTemplate
from kmd.model.operations_model import Operation, Source
from kmd.model.params_model import ALL_COMMON_PARAMS, Param, ParamList, ParamValues
from kmd.model.paths_model import StorePath
from kmd.model.preconditions_model import Precondition
from kmd.model.shell_model import ShellResult
from kmd.shell.shell_output import fill_text
from kmd.text_docs.diff_filters import DiffFilter
from kmd.text_docs.token_diffs import DIFF_FILTER_NONE
from kmd.text_docs.window_settings import WINDOW_NONE, WindowSettings
from kmd.util.format_utils import fmt_lines
from kmd.util.obj_utils import abbreviate_obj
from kmd.util.parse_key_vals import format_key_value
from kmd.util.string_template import StringTemplate

log = get_logger(__name__)


@dataclass(frozen=True)
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
    """
    Results from an action, including all items it produced as well as some hints
    about how to handle the result items.
    """

    items: List[Item]
    """Results from this action. Most often, just a single item."""

    replaces_input: bool = False
    """If True, a hint to archive the input items."""

    skip_duplicates: bool = False
    """If True, do not save duplicate items (based on identity)."""

    path_ops: Optional[List[PathOp]] = None
    """If specified, operations to perform on specific paths, such as selecting items."""

    shell_result: Optional[ShellResult] = None
    """Customize control of how the action's result is displayed in the shell."""

    def has_hints(self) -> bool:
        return bool(
            self.replaces_input or self.skip_duplicates or self.path_ops or self.shell_result
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


T = TypeVar("T")


@dataclass
class Action(ABC):
    """
    The base class for Actions, which are arbitrary operations that can be
    performed on Items. Instantiate this or a more specific subclass to create
    an action.

    Note we are careful to use immutable fields as much as possible, so subclassing
    is straightforward and doesn't require `field(default_factory=...)`.
    """

    name: str
    """
    The name of the action. Should be in lower_snake_case.
    """

    description: str
    """
    A description of the action, in a few sentences.
    """

    cacheable: bool = True
    """
    If True, the action execution may be skipped if the output is already present.
    """

    precondition: Precondition = Precondition.always
    """
    A precondition that must apply to all inputs to this action. Helps select whether
    an action is applicable to an item.
    """

    arg_type: ArgType = ArgType.Locator
    """
    The type of the arguments.
    """

    expected_args: ArgCount = ONE_ARG
    """
    The expected number of arguments. When an action is run per-item, this should
    be ONE_ARG.
    """

    output_type: ItemType = ItemType.doc
    """
    The type of the output item(s), which for now are all assumed to be of the same type.
    """

    expected_outputs: ArgCount = ONE_ARG
    """
    The number of outputs expected from this action.
    """

    run_per_item: bool = False
    """
    Normally, an action runs on all input items at once. If True, run the action separately
    for each input item, each time on a single item.
    """

    interactive_input: bool = False
    """
    Does this action ask for input interactively?
    """

    params: ParamList = ()
    """
    Parameters relevant to this action, which are settable when the action is invoked.
    These can be new parameters defined in a subclass, or more commonly, an existing
    common parameter (like an LLM) that is shared by several actions.
    """
    # TODO: Consider declaring if parameters are required.

    # More specific options that apply only to certain types of actions below.

    # Transform-specific options:
    windowing: WindowSettings = WINDOW_NONE
    diff_filter: DiffFilter = DIFF_FILTER_NONE

    # LLM-specific options:
    title_template: TitleTemplate = TitleTemplate("{title}")
    template: MessageTemplate = MessageTemplate("{body}")
    system_message: Message = Message("")

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

        for param in self.params:
            if not hasattr(self, param.name):
                raise InvalidActionDefinition(
                    f"Action `{self.name}` has parameter `{param.name}` but no corresponding field defined"
                )

    def signature(self) -> Signature:
        return Signature(self.arg_type, self.expected_args)

    def validate_args(self, args: Sequence[CommandArg]) -> None:
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

    def param_value_summary(self) -> Dict[str, str]:
        """
        Readable, serializable summary of the action's non-default parameters, to include in
        logs or metadata.
        """

        def stringify(value: Any) -> str:
            if isinstance(value, Enum):
                return value.name
            return str(value)

        changed_params: Dict[str, Any] = {}
        for param in self.params:
            if hasattr(self, param.name):
                value = getattr(self, param.name)
                if value:
                    changed_params[param.name] = stringify(value)
        return changed_params

    def param_value_summary_str(self) -> str:
        summary_str = fmt_lines(
            [format_key_value(name, value) for name, value in self.param_value_summary().items()]
        )
        return f"Parameters:\n{summary_str}"

    def _field_info(self, param_name: str) -> Optional[DataclassField]:
        return next((f for f in self.__dataclass_fields__.values() if f.name == param_name), None)

    def _param_info(self, param_name: str) -> Optional[Param]:
        return next((p for p in self.params if p.name == param_name), None)

    def with_param_values(
        self, new_values: ParamValues, strict: bool = False, overwrite: bool = False
    ) -> "Action":
        """
        Update the action with the additional parameter values and return a new Action.

        If strict is True, raise an error for unknown parameters, which we want to refuse
        for params set on the command line, but tolerate for params from workspace etc.

        Unless overwrite is True, do not overwrite existing parameter values.
        """
        new_instance = copy(self)  # Shallow copy.
        action_param_names = [param.name for param in self.params]

        overrides: List[str] = []
        for param_name, value_raw in new_values.items():
            # Sanity checks.
            if param_name not in ALL_COMMON_PARAMS and param_name not in action_param_names:
                if strict:
                    raise InvalidInput(
                        f"Unknown override param for action `{self.name}`: {param_name}"
                    )
                else:
                    log.warning(
                        "Ignoring inapplicable override param for action `%s`: %s",
                        self.name,
                        param_name,
                    )
                    continue

            param = self._param_info(param_name)

            # Set the field value on this action if the param applies to this action.
            if param:
                # Sanity check that the field type matches the param type.
                field_info = self._field_info(param_name)
                if field_info and not issubclass(cast(type, field_info.type), param.type):
                    log.warning(
                        "Parameter `%s` has field type %s in action `%s` but expected type %s",
                        param_name,
                        field_info.type,
                        self.name,
                        param.type,
                    )

                value = new_values.get(param_name, param.default_value, type=param.type)

                if not hasattr(new_instance, param_name) or overwrite:
                    setattr(new_instance, param_name, value)
                    overrides.append(format_key_value(param_name, value_raw))
                else:
                    log.info(
                        "Not overwriting existing parameter: keeping %s instead of %s",
                        format_key_value(param_name, getattr(new_instance, param_name)),
                        format_key_value(param_name, value_raw),
                    )
            else:
                log.info("Ignoring parameter for action `%s`: `%s`", self.name, param_name)

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

        For now, this only applies to actions with a single output, if self.cacheable is True.
        """
        log.info(
            "Preassemble check for `%s` is %s (%s with cacheable=%s)",
            self.name,
            self.cacheable and self.expected_outputs == ONE_ARG,
            self.expected_outputs,
            self.cacheable,
        )
        if self.cacheable and self.expected_outputs == ONE_ARG:
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
