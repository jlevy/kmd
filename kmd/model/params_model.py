from dataclasses import dataclass
from typing import Dict, Optional, Any, Type, List
from kmd.config.logger import get_logger
from kmd.config.settings import DEFAULT_CAREFUL_MODEL, DEFAULT_FAST_MODEL
from kmd.model.constants import LANGUAGE_LIST
from kmd.model.language_models import LLM_LIST
from kmd.text_docs.sizes import TextUnit
from kmd.util.type_utils import is_truthy


log = get_logger(__name__)


@dataclass(frozen=True)
class Param:
    """
    A settable parameter. May be used globally or as an option on a command or action.
    """

    name: str
    description: Optional[str] = None
    valid_values: Optional[List[str]] = None
    default_value: Optional[str] = None
    type: Type = str

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

    def parse(self, value: str) -> Optional[Any]:
        if value is None:
            return None
        try:
            if self.type == bool:
                return is_truthy(value)
            return self.type(value)
        except ValueError as e:
            raise ValueError(
                f"Invalid value for {self.name} (expected type {self.type.__name__}): {value}"
            ) from e

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
        default_value=DEFAULT_CAREFUL_MODEL.value,
    ),
    "assistant_model_fast": Param(
        "assistant_model_fast",
        "The name of the LLM used by the kmd assistant for fast responses.",
        LLM_LIST,
        default_value=DEFAULT_FAST_MODEL.value,
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

# Parameters that are available when an action is invoked.
RUNTIME_ACTION_PARAMS = {
    "rerun": Param(
        "rerun",
        "Rerun an action that would otherwise be skipped because the output already exists.",
        type=bool,
    ),
    # TODO: Implement.
    # "refetch": Param(
    #     "refetch",
    #     "Do not take content from media and web page caches. Re-fetch and update cache instead.",
    #     type=bool,
    # ),
}

USER_SETTABLE_PARAMS = {**GLOBAL_PARAMS, **COMMON_ACTION_PARAMS}

ALL_COMMON_PARAMS = {**GLOBAL_PARAMS, **COMMON_ACTION_PARAMS, **RUNTIME_ACTION_PARAMS}

ParamValues = Dict[str, Any]


def param_lookup(params: ParamValues, param_name: str, defaults: Dict[str, Param]) -> Optional[Any]:
    """
    Look up a parameter value, falling back to parameter defaults.
    """
    value = params.get(param_name)
    if value is None:
        param = defaults.get(param_name)
        if param is None:
            raise ValueError(f"Parameter not found: {param_name}")
        value = param.default_value
    return value


# TODO: Consider adding params for:
# - window settings
# - source extractor
# - citation formatter
# - web cache
