from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Dict, Generic, List, Optional, overload, Tuple, Type, TypeVar

from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.errors import InvalidParam
from kmd.model.constants import LANGUAGE_LIST
from kmd.model.language_models import LLM
from kmd.model.model_settings import DEFAULT_CAREFUL_LLM, DEFAULT_FAST_LLM
from kmd.text_docs.sizes import TextUnit
from kmd.util.format_utils import fmt_lines
from kmd.util.parse_key_vals import format_key_value
from kmd.util.type_utils import instantiate_as_type


log = get_logger(__name__)


T = TypeVar("T")


@dataclass(frozen=True)
class Param(Generic[T]):
    """
    Describes a settable parameter. This describes the parameter itself (including type and
    default value) but not its value. May be used globally or as an option to a command or
    action.
    """

    name: str

    description: Optional[str] = None

    default_value: Optional[T] = None

    type: Type = str

    valid_str_values: Optional[List[str]] = None
    """
    If the parameter is a string but still has only certain allowed values, list them here.
    Not necessary for enums, which are handled automatically.
    """

    def __post_init__(self):
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError(f"Not a valid param name: {repr(self.name)}")

    @property
    def default_value_str(self) -> Optional[str]:
        if self.default_value is None:
            return None
        elif issubclass(self.type, Enum):
            return self.type(self.default_value).name
        else:
            return str(self.default_value)

    @property
    def valid_values(self) -> List[str]:
        if self.valid_str_values:
            return self.valid_str_values
        elif issubclass(self.type, Enum):
            # Use the enum names as the valid values.
            return [e.name for e in self.type]
        else:
            return []  # Any value is allowed.

    @property
    def full_description(self) -> str:
        desc = self.description or ""

        if self.valid_values:
            val_list = ", ".join(f"`{v}`" for v in self.valid_values)
            if desc:
                desc += "\n\n"
            desc += f"Allowed values (type {self.type.__name__}): {val_list}"
        if self.default_value:
            if desc:
                desc += "\n\n"
            desc += f"Default value is: `{self.default_value}`"

        return desc

    @property
    def is_path(self) -> bool:
        return issubclass(self.type, Path)

    @property
    def shell_prefix(self) -> str:
        if self.type == bool:
            return f"--{self.name}"
        else:
            return f"--{self.name}="


# Parameters set globally such as in the workspace.
GLOBAL_PARAMS: Dict[str, Param] = {
    "assistant_model": Param(
        "assistant_model",
        "The name of the LLM used by the kmd assistant for regular (complex) requests.",
        default_value=DEFAULT_CAREFUL_LLM,
        type=LLM,
    ),
    "assistant_model_fast": Param(
        "assistant_model_fast",
        "The name of the LLM used by the kmd assistant for fast responses.",
        default_value=DEFAULT_FAST_LLM,
        type=LLM,
    ),
}

# Parameters that are common to all actions.
COMMON_ACTION_PARAMS: Dict[str, Param] = {
    "model": Param(
        "model",
        "The name of the LLM.",
        default_value=None,  # Let actions set defaults.
        type=LLM,
    ),
    "language": Param(
        "language",
        "The language of the input audio or text.",
        default_value=None,
        valid_str_values=LANGUAGE_LIST,
    ),
    "sentence_splitter": Param(
        "sentence_splitter",
        "The sentence splitter to use for splitting text into sentences.",
        default_value="spacy",
        valid_str_values=["spacy", "regex"],
    ),
    "chunk_size": Param(
        "chunk_size",
        "For actions that support it, process chunks of what size?",
        default_value=None,
        type=int,
    ),
    "chunk_unit": Param(
        "chunk_unit",
        "For actions that support it, the unit for measuring chunk size.",
        default_value=None,
        type=TextUnit,
    ),
    "md_template": Param(
        "md_template",
        """
        The markdown template to use for formatting. This is plain Markdown
        with curly-brace {name} variables for values to insert.
        """,
        default_value=None,
        type=Path,
    ),
}

# Extra parameters that are available when an action is invoked.
RUNTIME_ACTION_PARAMS: Dict[str, Param] = {
    "rerun": Param(
        "rerun",
        "Rerun an action that would otherwise be skipped because the output already exists.",
        type=bool,
    ),
}

USER_SETTABLE_PARAMS: Dict[str, Param] = {**GLOBAL_PARAMS, **COMMON_ACTION_PARAMS}

ALL_COMMON_PARAMS: Dict[str, Param] = {
    **GLOBAL_PARAMS,
    **COMMON_ACTION_PARAMS,
    **RUNTIME_ACTION_PARAMS,
}


def common_param(name: str) -> Param:
    """
    Get a standard, commonly used parameter by name.
    """

    param = ALL_COMMON_PARAMS.get(name)
    if param is None:
        raise InvalidParam(name)
    return param


def common_params(*names: str) -> Tuple[Param, ...]:
    return tuple(common_param(name) for name in names)


RawParamValue = str | bool
"""
Serialized string or boolean value for a parameter. May be converted to another type
like an enum. This type is compatible with command-line option values.
"""


ParamList = Tuple[Param, ...]


@dataclass
class ParamValues:
    """
    A set of parameter values. These are stored in raw (string or bool) format, since they
    are read in or persisted that way, but can be looked up with a type conversion.
    """

    values: Dict[str, RawParamValue] = field(default_factory=dict)

    def items(self):
        return self.values.items()

    def get_raw(
        self, param_name: str, defaults_info: Dict[str, Param] = ALL_COMMON_PARAMS
    ) -> Optional[RawParamValue]:
        """
        Look up a parameter value, falling back to parameter defaults.
        """
        value = self.values.get(param_name)
        if value is None:
            param = defaults_info.get(param_name)
            if param is None:
                raise InvalidParam(param_name)
            value = param.default_value_str
        return value

    @overload
    def get(
        self,
        param_name: str,
        default: T,
        type: Type[T] = str,
        defaults_info: Dict[str, Param] = ALL_COMMON_PARAMS,
    ) -> T: ...

    @overload
    def get(
        self,
        param_name: str,
        default: Optional[T] = None,
        type: Type[T] = str,
        defaults_info: Dict[str, Param] = ALL_COMMON_PARAMS,
    ) -> Optional[T]: ...

    def get(
        self,
        param_name: str,
        default: Optional[T] = None,
        type: Type[T] = str,
        defaults_info: Dict[str, Param] = ALL_COMMON_PARAMS,
    ) -> Optional[T]:
        value = self.get_raw(param_name, defaults_info)
        return instantiate_as_type(value, type) if value is not None else default

    def as_str(self) -> str:
        if self.items():
            return fmt_lines([format_key_value(name, value) for name, value in self.items()])
        else:
            return fmt_lines(["(no parameters)"])

    def as_str_brief(self):
        return str(self.values)

    def __str__(self):
        return self.as_str_brief()
