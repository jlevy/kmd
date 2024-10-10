from typing import List, Optional

from inflect import engine

from kmd.lang_tools.spacy_loader import nlp
from kmd.text_docs.wordtoks import is_word
from kmd.util.lazyobject import lazyobject
from kmd.util.log_calls import tally_calls


@lazyobject
def inflect():
    return engine()


def plural(word: str, count: Optional[int] = None) -> str:
    """
    Pluralize a word.
    """
    if not is_word(word):
        return word
    return inflect.plural(word, count)  # type: ignore


@tally_calls(level="warning", min_total_runtime=5)
def lemmatize(text: str) -> str:
    doc = nlp.en(text)
    return " ".join([token.lemma_ for token in doc])


def sort_by_length(values: List[str]) -> List[str]:
    return sorted(values, key=lambda x: (len(x), x))


def lemmatized_equal(text1: str, text2: str, lowercased: bool = True) -> bool:
    """
    Compare two texts to see if they are the same except for lemmatization.
    Ignores whitespace. Does not ignore punctuation.
    """
    if lowercased:
        text1 = " ".join(text1.split()).lower()
        text2 = " ".join(text2.split()).lower()
    return lemmatize(text1) == lemmatize(text2)
