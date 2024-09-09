from typing import List

from kmd.config.logger import get_logger
from kmd.lang_tools.spacy_loader import nlp
from kmd.util.log_calls import tally_calls

log = get_logger(__name__)


@tally_calls(level="warning", min_total_runtime=5)
def split_sentences_spacy(text: str) -> List[str]:
    """
    Split text into sentences using Spacy. (English.)
    """
    return [sent.text.strip() for sent in nlp.en(text).sents]
