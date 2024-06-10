from abc import abstractmethod
from textwrap import dedent
from typing import Any
import regex
from kmd.model.errors_model import ContentError, PreconditionFailure
from kmd.text_docs.wordtoks import SENT_BR_TOK, is_tag, raw_text_to_wordtoks


class Extractor:
    """
    Abstract base class for extractors that extract information from a document at a given location.
    """

    def __init__(self, doc_str: str):
        self.doc_str = doc_str

    def precondition_check(self) -> None:
        pass

    @abstractmethod
    def extract(self, wordtok_offset: int) -> Any:
        pass


class TimestampExtractor(Extractor):
    """
    Extract the first timestamp of the form `<span data-timestamp="123.45">` preceding the
    given location.
    """

    TIMESTAMP_RE = regex.compile(r'<span data-timestamp=[\'"](\d+(\.\d+)?)[\'"]')

    def __init__(self, doc_str: str):
        self.doc_str = doc_str
        self.wordtoks = raw_text_to_wordtoks(doc_str)
        if self.wordtoks[-1] != SENT_BR_TOK:
            self.wordtoks.append(SENT_BR_TOK)

    def precondition_check(self) -> None:
        if not self.TIMESTAMP_RE.search(self.doc_str):
            raise PreconditionFailure(
                'Document has no timestamps of the form `<span data-timestamp="123.45">`'
            )

    def extract(self, wordtok_offset: int) -> float:
        slice = self.wordtoks[:wordtok_offset]
        for wordtok in reversed(slice):
            if is_tag(wordtok):
                match = self.TIMESTAMP_RE.search(wordtok)
                if match:
                    return float(match.group(1))

        raise ContentError(
            f"No timestamp found after searching back {len(slice)} wordtoks from offset {wordtok_offset}"
        )


## Tests


def test_timestamp_extractor():
    doc_str = '<span data-timestamp="1.234">Sentence one.</span> <span data-timestamp="23">Sentence two.</span> Sentence three.'
    wordtoks = raw_text_to_wordtoks(doc_str)

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
            0: None ⎪<span data-timestamp="1.234">⎪
            1: 1.234 ⎪Sentence⎪
            2: 1.234 ⎪ ⎪
            3: 1.234 ⎪one⎪
            4: 1.234 ⎪.⎪
            5: 1.234 ⎪</span>⎪
            6: 1.234 ⎪ ⎪
            7: 1.234 ⎪<span data-timestamp="23">⎪
            8: 23.0 ⎪Sentence⎪
            9: 23.0 ⎪ ⎪
            10: 23.0 ⎪two⎪
            11: 23.0 ⎪.⎪
            12: 23.0 ⎪</span>⎪
            13: 23.0 ⎪ ⎪
            14: 23.0 ⎪Sentence⎪
            15: 23.0 ⎪ ⎪
            16: 23.0 ⎪three⎪
            17: 23.0 ⎪.⎪
            18: 23.0 ⎪<-SENT-BR->⎪
            """
        ).strip()
    )
