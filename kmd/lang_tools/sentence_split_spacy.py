from typing import List
from cachetools import cached
import spacy
from spacy.language import Language
from spacy.cli.download import download
from kmd.config.logger import get_logger
from kmd.util.log_calls import tally_calls

log = get_logger(__name__)


def spacy_download(model_name: str) -> Language:
    try:
        return spacy.load(model_name)
    except OSError:
        # If the model is not found, download it.
        log.message("Spacy model '%s' not found, so downloading it...", model_name)
        download(model_name)
        log.message("Downloaded Spacy model '%s'.", model_name)
        return spacy.load(model_name)


# Lazy load Spacy models.
class _Spacy:
    @cached(cache={})
    def load_model(self, model_name: str):
        return spacy_download(model_name)

    @property
    def en(self):
        return self.load_model("en_core_web_sm")


nlp = _Spacy()


@tally_calls(level="warning", min_total_runtime=5)
def split_sentences_spacy(text: str) -> List[str]:
    """
    Split text into sentences using Spacy. (English.)
    """
    return [sent.text.strip() for sent in nlp.en(text).sents]
