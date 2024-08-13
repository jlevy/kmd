from dataclasses import dataclass
from typing import Dict, Optional
from kmd.config.logger import get_logger
from kmd.config.settings import DEFAULT_CAREFUL_MODEL, DEFAULT_FAST_MODEL
from kmd.model.language_models import MODEL_LIST
from kmd.text_docs.sizes import TextUnit


log = get_logger(__name__)

# Just a common language list.
# Currently the main languages supported by DeepGram nova-2.
LANGUAGES = [
    "bg",
    "ca",
    "zh",
    "cs",
    "da",
    "nl",
    "en",
    "et",
    "fi",
    "fr",
    "de",
    "el",
    "hi",
    "hu",
    "id",
    "it",
    "ja",
    "ko",
    "lv",
    "lt",
    "ms",
    "no",
    "pl",
    "pt",
    "ro",
    "ru",
    "sk",
    "es",
    "sv",
    "th",
    "tr",
    "uk",
    "vi",
]


@dataclass(frozen=True)
class Param:
    name: str
    description: str
    valid_values: Optional[list[str]]
    default_value: Optional[str]

    def full_description(self) -> str:
        desc = self.description
        if self.valid_values:
            val_list = ", ".join(f"`{v}`" for v in self.valid_values)
            desc += f"\n\nAllowed values are: {val_list}"
        if self.default_value:
            desc += f"\n\nDefault value is: `{self.default_value}`"
        return desc


PARAMS = {
    "model": Param(
        "model",
        "The name of the LLM.",
        MODEL_LIST,
        default_value=None,  # Let actions set defaults.
    ),
    "language": Param(
        "language",
        "The language of the input audio or text.",
        LANGUAGES,
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


ParamSet = Dict[str, str]


def get_param(params: ParamSet, param_name: str) -> Optional[str]:
    value = params.get(param_name)
    if value is None:
        param = PARAMS.get(param_name)
        if param is None:
            raise ValueError(f"Parameter not found: {param_name}")
        value = param.default_value
    return value


# TODO: Add params for:
# - window settings
# - source extractor
# - citation formatter
# - chunk size (e.g. citations per sentence or per pagagraph)
# - web cache
