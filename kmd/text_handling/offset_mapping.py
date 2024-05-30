from textwrap import dedent
from typing import Dict
from kmd.text_handling.text_diffs import DiffTag, lcs_diff_wordtoks

from kmd.text_handling.text_doc import TextDoc


class OffsetMapping:
    """
    Given two documents doc1 and doc2 as a sequence of word tokens, create a mapping from offsets
    in doc2 back to doc1.
    """

    def __init__(
        self, doc1: TextDoc, doc2: TextDoc, min_wordtoks: int = 8, max_diff_frac: float = 0.4
    ):
        self.doc1 = doc1
        self.doc2 = doc2
        self.wordtoks1 = list(doc1.as_wordtoks())
        self.wordtoks2 = list(doc2.as_wordtoks())
        self.diff = lcs_diff_wordtoks(self.wordtoks1, self.wordtoks2)
        self._validate(min_wordtoks, max_diff_frac)
        self.map: Dict[int, int] = {}
        self._create_mapping()

    def map_back(self, offset2: int) -> int:
        return self.map[offset2]

    def _validate(self, min_wordtoks: int, max_diff_frac: float):
        if len(self.wordtoks1) < min_wordtoks or len(self.wordtoks2) < min_wordtoks:
            raise ValueError(f"Documents should have at least {min_wordtoks} wordtoks")

        nchanges = len(self.diff.changes())
        if float(nchanges) / len(self.wordtoks1) > max_diff_frac:
            raise ValueError(
                f"Documents have too many changes: {nchanges}/{len(self.wordtoks1)} ({float(nchanges) / len(self.wordtoks1):.2f} > {max_diff_frac})"
            )

    def _create_mapping(self):
        offset1 = 0
        offset2 = 0
        last_offset1 = 0

        for op in self.diff.ops:
            if op.action == DiffTag.EQUAL:
                for _ in op.wordtoks:
                    self.map[offset2] = offset1
                    last_offset1 = offset1
                    offset1 += 1
                    offset2 += 1
            elif op.action == DiffTag.DELETE:
                for _ in op.wordtoks:
                    self.map[offset2] = last_offset1
                    offset1 += 1
            elif op.action == DiffTag.INSERT:
                for _ in op.wordtoks:
                    self.map[offset2] = last_offset1
                    offset2 += 1

    def __str__(self):
        return f"OffsetMapping(doc1 len {len(self.wordtoks1)}, doc2 len {len(self.wordtoks2)}, mapping len {len(self.map)})"


## Tests


def test_offset_mapping():
    doc1 = TextDoc.from_text("This is a simple test.")
    doc2 = TextDoc.from_text("This is a simpler pytest.")

    mapping = OffsetMapping(doc1, doc2)
    wordtoks1 = mapping.wordtoks1
    wordtoks2 = mapping.wordtoks2

    mapping_str = "\n".join(
        f"{i} ({wordtoks2[i]}) -> {mapping.map_back(i)} ({wordtoks1[mapping.map_back(i)]})"
        for i in range(len(wordtoks2))
    )
    print(mapping)
    print(mapping.map)

    print(mapping_str)

    assert (
        mapping_str
        == dedent(
            """
            0 (This) -> 0 (This)
            1 ( ) -> 1 ( )
            2 (is) -> 2 (is)
            3 ( ) -> 3 ( )
            4 (a) -> 4 (a)
            5 ( ) -> 5 ( )
            6 (simpler) -> 5 ( )
            7 ( ) -> 7 ( )
            8 (pytest) -> 7 ( )
            9 (.) -> 9 (.)
            """
        ).strip()
    )
