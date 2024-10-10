from typing import Any, Dict, List, Optional, Type

from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.model.constants import LANGUAGE_LIST
from kmd.model.language_models import LLM_LIST
from kmd.model.model_settings import DEFAULT_CAREFUL_LLM, DEFAULT_FAST_LLM
from kmd.text_docs.sizes import TextUnit
from kmd.util.format_utils import fmt_lines
from kmd.util.parse_key_vals import format_key_value


log = get_logger(__name__)


@dataclass(frozen=True)
class Param:
    """
    Describes a settable parameter. This describes the parameter itself (including type and
    default value) but not its value. May be used globally or as an option to a command or
    action.
    """

    name: str
    description: Optional[str] = None
    valid_values: Optional[List[str]] = None
    default_value: Optional[str] = None
    type: Type = str

    def __post_init__(self):
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError(f"Not a valid param name: {repr(self.name)}")

    def full_description(self) -> str:
        desc = self.description or ""
        if self.type is str:
            if self.valid_values:
                val_list = ", ".join(f"`{v}`" for v in self.valid_values)
                if desc:
                    desc += "\n\n"
                desc += f"Allowed values are: {val_list}"
            if self.default_value:
                if desc:
                    desc += "\n\n"
                desc += f"Default value is: `{self.default_value}`"
        else:
            if desc:
                desc += "\n\n"
            desc += f"Type: `{self.type.__name__}`"

        return desc

    def shell_prefix(self) -> str:
        if self.type == bool:
            return f"--{self.name}"
        else:
            return f"--{self.name}="


# Parameters set globally such as in the workspace.
GLOBAL_PARAMS = {
    "assistant_model": Param(
        "assistant_model",
        "The name of the LLM used by the kmd assistant for regular (complex) requests.",
        LLM_LIST,
        default_value=DEFAULT_CAREFUL_LLM.value,
    ),
    "assistant_model_fast": Param(
        "assistant_model_fast",
        "The name of the LLM used by the kmd assistant for fast responses.",
        LLM_LIST,
        default_value=DEFAULT_FAST_LLM.value,
    ),
}

# Parameters that are common to all actions.
COMMON_ACTION_PARAMS = {
    "model": Param(
        "model",
        "The name of the LLM.",
        LLM_LIST,
        default_value=None,  # Let actions set defaults.
    ),
    "language": Param(
        "language",
        "The language of the input audio or text.",
        LANGUAGE_LIST,
        default_value=None,
    ),
    "chunk_size": Param(
        "chunk_size",
        "For actions that support it, process chunks of what size?",
        valid_values=None,
        default_value=None,
    ),
    "chunk_unit": Param(
        "chunk_unit",
        "For actions that support it, the unit for measuring chunk size.",
        [chunk_unit.value for chunk_unit in TextUnit],
        default_value=None,
    ),
    "sentence_splitter": Param(
        "sentence_splitter",
        "The sentence splitter to use for splitting text into sentences.",
        ["spacy", "regex"],
        default_value="spacy",
    ),
}

# Extra parameters that are available when an action is invoked.
RUNTIME_ACTION_PARAMS = {
    "rerun": Param(
        "rerun",
        "Rerun an action that would otherwise be skipped because the output already exists.",
        type=bool,
    ),
}

USER_SETTABLE_PARAMS = {**GLOBAL_PARAMS, **COMMON_ACTION_PARAMS}

ALL_COMMON_PARAMS = {**GLOBAL_PARAMS, **COMMON_ACTION_PARAMS, **RUNTIME_ACTION_PARAMS}


class ParamSettings:
    """
    A set of parameter values. These are in raw string or bool format, since they
    are persisted that way.
    """

    def __init__(self, params: Optional[Dict[str, str | bool]] = None):
        self.params = params or {}

    def items(self):
        return self.params.items()

    def lookup(self, param_name: str, defaults: Dict[str, Param]) -> Optional[Any]:
        """
        Look up a parameter value, falling back to parameter defaults.
        """
        value = self.params.get(param_name)
        if value is None:
            param = defaults.get(param_name)
            if param is None:
                raise ValueError(f"Parameter not found: {param_name}")
            value = param.default_value
        return value

    def as_str(self) -> str:
        if self.items():
            return fmt_lines([format_key_value(name, value) for name, value in self.items()])
        else:
            return fmt_lines(["(no parameters)"])

    def as_str_brief(self):
        return str(self.params)

    def __str__(self):
        return self.as_str_brief()
