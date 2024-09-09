from functools import cached_property
from textwrap import dedent
from typing import List

import regex

from kmd.config.logger import get_logger
from kmd.model.errors_model import ContentError, PreconditionFailure
from kmd.provenance.extractors import Extractor
from kmd.text_docs.wordtoks import raw_text_to_wordtoks, search_tokens

log = get_logger(__name__)


TIMESTAMP_RE = regex.compile(r'<span data-timestamp=[\'"](\d+(\.\d+)?)[\'"]')


def _extract_timestamp(wordtok: str):
    match = TIMESTAMP_RE.search(wordtok)
    return float(match.group(1)) if match else None


def _is_timestamp(wordtok: str):
    return bool(_extract_timestamp(wordtok))


class TimestampExtractor(Extractor):
    """
    Extract the first timestamp of the form `<span data-timestamp="123.45">` preceding the
    given location.
    """

    def __init__(self, doc_str: str):
        self.doc_str = doc_str

    @cached_property
    def wordtoks(self) -> List[str]:
        wordtoks = raw_text_to_wordtoks(self.doc_str, parse_para_br=True, bof_eof=True)
        return wordtoks

    def precondition_check(self) -> None:
        if not TIMESTAMP_RE.search(self.doc_str):
            raise PreconditionFailure(
                'Document has no timestamps of the form `<span data-timestamp="123.45">`'
            )

    def extract(self, wordtok_offset: int) -> float:
        try:
            _index, wordtok = (
                search_tokens(self.wordtoks).at(wordtok_offset).seek_back(_is_timestamp).get_token()
            )
            if wordtok:
                timestamp = _extract_timestamp(wordtok)
                if timestamp is not None:
                    return timestamp
            raise ContentError(f"No timestamp found seeking back from {wordtok_offset}: {wordtok}")
        except KeyError as e:
            raise ContentError(f"No timestamp found searching back from {wordtok_offset}: {e}")


## Tests


def test_timestamp_extractor():
    doc_str = '<span data-timestamp="1.234">Sentence one.</span> <span data-timestamp="23">Sentence two.</span> Sentence three.'

    extractor = TimestampExtractor(doc_str)
    extractor.precondition_check()
    wordtoks = extractor.wordtoks

    results = []
    for i, wordtok in enumerate(wordtoks):
        try:
            timestamp = extractor.extract(i)
        except ContentError:
            timestamp = None
        results.append(f"{i}: {timestamp} ⎪{wordtok}⎪")

    print("\n".join(results))

    assert (
        "\n".join(results)
        == dedent(
            """
            0: None ⎪<-BOF->⎪
            1: None ⎪<span data-timestamp="1.234">⎪
            2: 1.234 ⎪Sentence⎪
            3: 1.234 ⎪ ⎪
            4: 1.234 ⎪one⎪
            5: 1.234 ⎪.⎪
            6: 1.234 ⎪</span>⎪
            7: 1.234 ⎪ ⎪
            8: 1.234 ⎪<span data-timestamp="23">⎪
            9: 23.0 ⎪Sentence⎪
            10: 23.0 ⎪ ⎪
            11: 23.0 ⎪two⎪
            12: 23.0 ⎪.⎪
            13: 23.0 ⎪</span>⎪
            14: 23.0 ⎪ ⎪
            15: 23.0 ⎪Sentence⎪
            16: 23.0 ⎪ ⎪
            17: 23.0 ⎪three⎪
            18: 23.0 ⎪.⎪
            19: 23.0 ⎪<-EOF->⎪
            """
        ).strip()
    )
