from typing import Callable, List
from cachetools import cached
import regex
import spacy
from spacy.language import Language
from spacy.cli.download import download
from kmd.config.logger import get_logger
from kmd.util.log_calls import log_calls

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


@log_calls(level="message", if_slower_than=0.1)
def split_sentences(text: str) -> List[str]:
    """
    Split text into sentences using Spacy. (English.)
    """
    return [sent.text.strip() for sent in nlp.en(text).sents]


# This is a heuristic from Flowmark:
# https://github.com/jlevy/atom-flowmark/blob/master/lib/remark-smart-word-wrap.js#L17-L33

# Heuristic: End of sentence must be two letters or more, with the last letter lowercase,
# followed by a period, exclamation point, question mark, colon, or semicolon.
# Except for colon or semicolon, a final or preceding parenthesis or quote is allowed.
# TODO: Could also handle rare cases with quotes and parentheses at sentence end.
# TODO: Should be OK for most Latin languages but may need to rethink 2-letter restriction.
SENTENCE_RE = regex.compile(r"(\p{L}[\p{Ll}])([.?!]['\"’”)]?|['\"’”)][.?!]|[:;]) *$")


def heuristic_end_of_sentence(word: str) -> bool:
    return bool(SENTENCE_RE.search(word))


def split_sentences_fast(
    text: str, heuristic: Callable[[str], bool] = heuristic_end_of_sentence
) -> List[str]:
    """
    Split text into sentences using an approximate, fast regex heuristic. (English.)
    Goal is to be conservative, not perfect, avoiding excessive breaks.
    """
    words = text.split()
    sentences = []
    sentence = []
    for word in words:
        sentence.append(word)
        if heuristic(word):
            sentences.append(" ".join(sentence))
            sentence = []
    if sentence:
        sentences.append(" ".join(sentence))
    return sentences
