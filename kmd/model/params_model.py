from dataclasses import dataclass
from enum import Enum
from typing import Optional
from kmd.config.logger import get_logger
from kmd.model.language_models import MODEL_LIST


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

    def full_description(self) -> str:
        desc = self.description
        if self.valid_values:
            desc += f" Allowed values are: {', '.join(self.valid_values)}"
        return desc


ACTION_PARAMS = {
    "model": ActionParam(
        "model",
        "The name of the LLM.",
        MODEL_LIST,
    ),
    "chunk_size": ActionParam(
        "chunk_size",
        "Process what size chunks?",
        [chunk_size.value for chunk_size in ChunkSize],
    ),
}

# TODO: Add params for:
# - window settings
# - source extractor
# - citation formatter
# - chunk size (e.g. citations per sentence or per pagagraph)
