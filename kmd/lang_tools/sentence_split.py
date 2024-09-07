from typing import Callable, List, Optional
from kmd.file_storage.workspaces import get_param_value
from kmd.lang_tools.sentence_split_regex import split_sentences_regex
from kmd.lang_tools.sentence_split_spacy import split_sentences_spacy
from kmd.util.type_utils import not_none


Splitter = Callable[[str], List[str]]


def get_sentence_splitter(name: str) -> Splitter:
    if name not in ["spacy", "regex"]:
        raise ValueError(f"Unknown sentence splitter: {name}")
    if name == "spacy":
        return split_sentences_spacy
    else:
        return split_sentences_regex


def split_sentences(text: str, splitter: Optional[Splitter] = None) -> List[str]:
    """
    Split sentences. Regex is much faster then Spacy so splitter is specifiable as
    a value or a workspace param.
    """
    if splitter is None:
        splitter = get_sentence_splitter(not_none(get_param_value("sentence_splitter")))

    return splitter(text)
