from dataclasses import dataclass
from typing import Dict, Optional, Any, Type
from kmd.config.logger import get_logger
from kmd.config.settings import DEFAULT_CAREFUL_MODEL, DEFAULT_FAST_MODEL
from kmd.model.constants import LANGUAGE_LIST
from kmd.model.language_models import MODEL_LIST
from kmd.text_docs.sizes import TextUnit


log = get_logger(__name__)


def is_truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on", "y")
    return bool(value)


@dataclass(frozen=True)
class Param:
    """
    A settable parameter. May be used globally or as an option on a command or action.
    """

    name: str
    description: str
    valid_values: Optional[list[str]]
    default_value: Optional[str]
    type: Type = str

    def full_description(self) -> str:
        desc = self.description
        if self.type is str:
            if self.valid_values:
                val_list = ", ".join(f"`{v}`" for v in self.valid_values)
                desc += "\n\n"
                desc += f"Allowed values are: {val_list}"
            if self.default_value:
                desc += "\n\n"
                desc += f"Default value is: `{self.default_value}`"
        else:
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


# Some parameters that make sense to be settable globally.
GLOBAL_PARAMS = {
    "model": Param(
        "model",
        "The name of the LLM.",
        MODEL_LIST,
        default_value=None,  # Let actions set defaults.
    ),
    "language": Param(
        "language",
        "The language of the input audio or text.",
        LANGUAGE_LIST,
        default_value=None,
    ),
    "assistant_model": Param(
        "assistant_model",
        "The name of the LLM used by the kmd assistant for regular (complex) requests.",
        MODEL_LIST,
        default_value=DEFAULT_CAREFUL_MODEL.value,
    ),
    "assistant_model_fast": Param(
        "assistant_model_fast",
        "The name of the LLM used by the kmd assistant for fast responses.",
        MODEL_LIST,
        default_value=DEFAULT_FAST_MODEL.value,
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
}

GLOBAL_PARAM_NAMES = set(GLOBAL_PARAMS.keys())


ParamValues = Dict[str, Any]


def param_lookup(
    params: ParamValues, param_name: str, defaults: Dict[str, Param] = GLOBAL_PARAMS
) -> Optional[Any]:
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
# - chunk size (e.g. citations per sentence or per pagagraph)
# - web cache
