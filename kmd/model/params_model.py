from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
from kmd.config.logger import get_logger
from kmd.model.language_models import LLM, MODEL_LIST


log = get_logger(__name__)


class ChunkSize(Enum):
    """
    The size of a chunk used by different actions.
    TODO: Could add a quantity to offer more flexibility.
    """

    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"


@dataclass(frozen=True)
class ActionParam:
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


ACTION_PARAMS = {
    "model": ActionParam(
        "model",
        "The name of the LLM.",
        MODEL_LIST,
        default_value=None,
    ),
    "assistant_model": ActionParam(
        "assistant_model",
        "The name of the LLM used by the kmd assistant for regular (complex) requests.",
        MODEL_LIST,
        default_value=LLM.claude_3_5_sonnet.value,
    ),
    "assistant_model_fast": ActionParam(
        "assistant_model_fast",
        "The name of the LLM used by the kmd assistant for fast responses.",
        MODEL_LIST,
        default_value=LLM.groq_llama_3_1_8b_instant.value,
    ),
    "chunk_size": ActionParam(
        "chunk_size",
        "For actions that support more than one kind of chunk, process what size of chunk?",
        [chunk_size.value for chunk_size in ChunkSize],
        default_value=None,
    ),
}


ParamSet = Dict[str, str]


def get_action_param(params: ParamSet, param_name: str) -> Optional[str]:
    value = params.get(param_name)
    if value is None:
        param = ACTION_PARAMS.get(param_name)
        if param is None:
            raise ValueError(f"Action parameter not found: {param_name}")
        value = param.default_value
    return value


# TODO: Add params for:
# - window settings
# - source extractor
# - citation formatter
# - chunk size (e.g. citations per sentence or per pagagraph)
# - web cache
