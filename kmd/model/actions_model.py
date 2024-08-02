from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from kmd.config.logger import get_logger
from kmd.lang_tools.capitalization import capitalize_cms
from kmd.config.text_styles import EMOJI_WARN
from kmd.model.errors_model import ContentError, InvalidInput
from kmd.model.items_model import Item
from kmd.lang_tools.inflection import plural
from kmd.model.params_model import ACTION_PARAMS, ChunkSize
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
        super().__init__(template, allowed_fields=["title", "action_name"])


class LLMTemplate(StringTemplate):
    """A template for an LLM request."""

    def __init__(self, template: str):
        super().__init__(template, allowed_fields=["body"])


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


# TODO: frozen=True
@dataclass
class Action(ABC):
    """
    The base classes for Actions, which are arbitrary operations that can be
    performed on Items. Instantiate this or a more specific subclass to create
    an action.
    """

    name: str
    description: str
    implementation: str = "builtin"
    friendly_name: Optional[str] = None
    model: Optional[str] = None
    chunk_size: Optional[ChunkSize] = None
    title_template: Optional[TitleTemplate] = None
    template: Optional[LLMTemplate] = None
    system_message: Optional[str] = None
    expected_args: ExpectedArgs = field(default_factory=lambda: ONE_ARG)
    interactive_input: bool = False

    def __post_init__(self):
        self.friendly_name = self.friendly_name or capitalize_cms(
            self.name, underscores_to_spaces=True
        )
        self.friendly_name = clean_description(self.friendly_name)
        self.description = clean_description(self.description)

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

    def update_with_params(self, params: Dict[str, str]) -> "Action":
        """
        Update the action with the given parameters and return a new Action.
        """
        new_instance = deepcopy(self)

        for name, value in params.items():
            if name in vars(new_instance) and name in ACTION_PARAMS:
                current_value = getattr(new_instance, name)
                if current_value != value:
                    setattr(new_instance, name, value)
                    log.message(
                        "Overriding parameter for action %s: %s",
                        self.name,
                        format_key_value(name, value),
                    )

        return new_instance

    @abstractmethod
    def run(self, items: ActionInput) -> ActionResult:
        pass

    def __str__(self):
        return abbreviate_obj(self)


@dataclass
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
