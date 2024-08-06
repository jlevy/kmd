from abc import ABC, abstractmethod
from copy import copy
from dataclasses import dataclass, field, fields
from textwrap import dedent
from typing import Dict, List, Optional
from kmd.config.logger import get_logger
from kmd.config.text_styles import EMOJI_WARN
from kmd.model.errors_model import ContentError, InvalidInput
from kmd.model.items_model import UNTITLED, Item, ItemType
from kmd.lang_tools.inflection import plural
from kmd.model.operations_model import Operation, Source
from kmd.model.params_model import ACTION_PARAMS, TextUnit
from kmd.model.preconditions_model import Precondition
from kmd.text_formatting.text_formatting import clean_description
from kmd.util.obj_utils import abbreviate_obj
from kmd.util.parse_utils import format_key_value
from kmd.util.string_template import StringTemplate


log = get_logger(__name__)


@dataclass(frozen=True)
class ExpectedArgs:
    min_args: Optional[int]
    max_args: Optional[int]


NO_ARGS = ExpectedArgs(0, 0)
ONE_ARG = ExpectedArgs(1, 1)
ONE_OR_NO_ARGS = ExpectedArgs(0, 1)
TWO_ARGS = ExpectedArgs(2, 2)
ANY_ARGS = ExpectedArgs(0, None)
ONE_OR_MORE_ARGS = ExpectedArgs(1, None)


class TitleTemplate(StringTemplate):
    """A template for a title."""

    def __init__(self, template: str):
        super().__init__(template.strip(), allowed_fields=["title", "action_name"])


class LLMTemplate(StringTemplate):
    """A template for an LLM request."""

    def __init__(self, template: str):
        super().__init__(dedent(template), allowed_fields=["body"])


class LLMMessage(str):
    """A message for an LLM."""

    def __new__(cls, value: str):
        return super().__new__(cls, dedent(value))


# For now these are simple but we will want to support other hints or output data in the future.
ActionInput = List[Item]


@dataclass
class ActionResult:
    items: List[Item]
    """Results from this action. Most often, just a single item."""

    replaces_input: bool = False
    """If True, a hint to archive the input items."""

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

    expected_args: ExpectedArgs = field(default_factory=lambda: ONE_ARG)
    """The required number of arguments."""

    interactive_input: bool = False
    """Does this action ask for input interactively?"""

    # These are set if they make sense, i.e. it's an LLM action.
    model: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_unit: Optional[TextUnit] = None
    title_template: Optional[TitleTemplate] = None
    template: Optional[LLMTemplate] = None
    system_message: Optional[LLMMessage] = None

    def __post_init__(self):
        # Class is frozen but we do want to update the description.
        object.__setattr__(self, "description", clean_description(self.description))

    def validate_args(self, args: List[str]) -> None:
        if len(args) != 0 and self.expected_args == NO_ARGS:
            raise InvalidInput(f"Action {self.name} does not expect any arguments")
        if len(args) != 1 and self.expected_args == ONE_ARG:
            raise InvalidInput(f"Action {self.name} expects exactly one argument")
        if self.expected_args.max_args is not None and len(args) > self.expected_args.max_args:
            raise InvalidInput(
                f"Action {self.name} expects at most {self.expected_args.max_args} arguments"
            )
        if self.expected_args.min_args is not None and len(args) < self.expected_args.min_args:
            raise InvalidInput(
                f"Action {self.name} expects at least {self.expected_args.min_args} arguments"
            )

    def validate_precondition(self, items: ActionInput) -> None:
        if self.precondition:
            for item in items:
                self.precondition.check(item)

    def update_with_params(self, params: Dict[str, str]) -> "Action":
        """
        Update the action with the given parameters and return a new Action.
        """
        new_instance = copy(self)  # Shallow copy.
        action_fields = fields(self)

        for name, value in params.items():
            if name in ACTION_PARAMS and name in action_fields:
                # Use object.__setattr__ to update the frozen instance.
                object.__setattr__(new_instance, name, value)
                log.message(
                    "Overriding parameter for action `%s`: %s",
                    self.name,
                    format_key_value(name, value),
                )
            else:
                log.warning("Ignoring unknown override param for action `%s`: %s", self.name, name)

        return new_instance

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
class EachItemAction(Action):
    """
    An action that simply processes each arg one after the other. It does not abort for
    content-related errors but will fail on other errors.
    """

    def run(self, items: ActionInput) -> ActionResult:
        result_items = []
        errors = []
        log.message("Running EachItemAction %s on each of %s items", self.name, len(items))

        for item in items:
            try:
                result_item = self.run_item(item)
                result_items.append(result_item)
            except (ContentError, InvalidInput) as e:
                errors.append(e)
                log.error(
                    "Error processing item (will continue with others): %s: %s",
                    e,
                    item,
                )

        if errors:
            log.error(
                "%s %s %s occurred while processing items. See above!",
                EMOJI_WARN,
                len(errors),
                plural("error", len(errors)),
            )
        return ActionResult(result_items)

    @abstractmethod
    def run_item(self, item: Item) -> Item:
        pass


def preassemble_single_output(
    operation: Operation, action: Action, items: ActionInput, **kwargs
) -> Item:
    """
    Assemble a single output item from the given input items, copying the first
    input item as a template and empty body.
    """
    primary_input = items[0]
    item = primary_input.derived_copy(body=None, **kwargs)

    if action.title_template:
        item.title = action.title_template.format(title=primary_input.title or UNTITLED)

    item.update_history(Source(operation=operation, output_num=0))

    return item


@dataclass(frozen=True)
class CachedTextAction(EachItemAction):
    """
    A simple action that processes each input returns a single text output for each,
    with the output title etc. derived from the first input item. Caches and skips
    items that have already been processed.
    """

    # Implementing this makes caching work.
    def preassemble(self, operation: Operation, items: ActionInput) -> Optional[ActionResult]:
        return ActionResult([preassemble_single_output(operation, self, items, type=ItemType.note)])
