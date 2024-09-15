from abc import ABC, abstractmethod
from typing import Any

from kmd.config.logger import get_logger

log = get_logger(__name__)


class Extractor(ABC):
    """
    Abstract base class for extractors that extract information from a document at a given location.
    """

    def __init__(self, doc_str: str):
        self.doc_str = doc_str

    @abstractmethod
    def extract(self, wordtok_offset: int) -> Any:
        pass
