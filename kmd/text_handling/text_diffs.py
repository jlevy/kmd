from dataclasses import dataclass
import difflib
from enum import Enum
from textwrap import dedent
from typing import Any, Callable, List, Optional, Tuple
from kmd.text_handling.text_doc import DocIndex, TextDoc
from kmd.text_handling.wordtoks import is_br_or_space, is_word


class DiffTag(Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"

    def as_plus_minus(self):
        return "+" if self == DiffTag.INSERT else "-" if self == DiffTag.DELETE else " "


@dataclass
class DiffOp:
    action: DiffTag
    wordtoks: List[str]

    def filter(self, pred: Callable[[str], bool]):
        return DiffOp(self.action, [tok for tok in self.wordtoks if pred(tok)])

    def __str__(self):
        if self.wordtoks:
            return f"{self.action.as_plus_minus()} {", ".join(repr(tok) for tok in self.wordtoks)},"
        else:
            return "(empty DiffOp)"


@dataclass
class TokenDiffStats:
    added: int
    removed: int

    def nchanges(self) -> int:
        return self.added + self.removed


@dataclass
class TextDiff:
    """
    A diff of two texts as a sequence of EQUAL, INSERT, and DELETE operations.
    """

    ops: List[DiffOp]

    def changes(self) -> List[DiffOp]:
        return [op for op in self.ops if op.action != DiffTag.EQUAL]

    def stats(self) -> TokenDiffStats:
        wordtoks_added = sum(len(op.wordtoks) for op in self.ops if op.action == DiffTag.INSERT)
        wordtoks_removed = sum(len(op.wordtoks) for op in self.ops if op.action == DiffTag.DELETE)
        return TokenDiffStats(wordtoks_added, wordtoks_removed)

    def __str__(self):
        if len(self.changes()) == 0:
            return "TextDiff: (no changes)"
        else:
            return "TextDiff:\n" + "\n".join(str(op) for op in self.ops)


def lcs_diff_wordtoks(wordtoks1: List[str], wordtoks2: List[str]) -> TextDiff:
    """
    Perform an LCS-style diff on two lists of wordtoks.
    """
    s = difflib.SequenceMatcher(None, wordtoks1, wordtoks2)
    diff: List[DiffOp] = []

    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == "equal":
            diff.append(DiffOp(DiffTag.EQUAL, wordtoks1[i1:i2]))
        elif tag == "insert":
            diff.append(DiffOp(DiffTag.INSERT, wordtoks2[j1:j2]))
        elif tag == "delete":
            diff.append(DiffOp(DiffTag.DELETE, wordtoks1[i1:i2]))
        elif tag == "replace":
            diff.append(DiffOp(DiffTag.DELETE, wordtoks1[i1:i2]))
            diff.append(DiffOp(DiffTag.INSERT, wordtoks2[j1:j2]))

    return TextDiff(diff)


def scored_lcs_diff(wordtoks1: List[str], wordtoks2: List[str]) -> Tuple[float, TextDiff]:
    """
    Calculate the number of wordtoks added and removed between two TextDocs.
    Score is (wordtoks_added + wordtoks_removed) / min(len(doc1), len(doc2)),
    which is 0 for identical docs.
    """

    if len(wordtoks1) == 0 or len(wordtoks2) == 0:
        raise ValueError("Cannot score diff for empty documents")

    diff = lcs_diff_wordtoks(wordtoks1, wordtoks2)
    score = float(diff.stats().nchanges()) / min(len(wordtoks1), len(wordtoks2))
    return score, diff


def find_best_alignment(
    list1: List[str],
    list2: List[str],
    min_overlap: int,
    max_overlap: Optional[int] = None,
    scored_diff: Callable[[List[str], List[str]], Tuple[float, Any]] = scored_lcs_diff,
) -> Tuple[int, float, Any]:
    """
    Find the best alignment of two lists of values, where edit distance is smallest but overlap is
    at least min_overlap and at most max_overlap. Returns offset into list1 and diff object.
    """
    len1, len2 = len(list1), len(list2)
    best_offset = -1
    best_score = float("inf")
    best_diff = None
    max_overlap = min(len1, len2, max_overlap) if max_overlap is not None else min(len1, len2)

    if min_overlap > len1 or min_overlap > len2:
        raise ValueError(
            f"Minimum overlap {min_overlap} is greater than the length of one of the lists ({len1}, {len2})"
        )

    # Slide the second list over the first list, starting from the end of the first list.
    # TODO: This could be much more efficient by being cleverer about reusing diff calculations.
    for overlap in range(min_overlap, max_overlap + 1):
        start1 = len1 - overlap
        end1 = len1
        start2 = 0
        end2 = overlap

        score, diff = scored_diff(list1[start1:end1], list2[start2:end2])

        if score < best_score:
            best_score = score
            best_offset = start1
            best_diff = diff

    if best_diff is None:
        raise ValueError("No alignment found")

    return best_offset, best_score, best_diff


def diff_non_br_whitespace(diff: TextDiff) -> TextDiff:
    """
    Return any diff operations that are not simply changes to whitespace and paragraph breaks.
    """
    ops = []
    for op in diff.changes():
        match = op.filter(lambda tok: not is_br_or_space(tok))
        if len(match.wordtoks) > 0:
            ops.append(match)
    return TextDiff(ops)


def diff_non_punctuation_whitespace(diff: TextDiff) -> TextDiff:
    """
    Return any diff operations that are not simply changes to punctuation or whitespace.
    """
    ops = []
    for op in diff.changes():
        match = op.filter(lambda tok: bool(is_word(tok)))
        if len(match.wordtoks) > 0:
            ops.append(match)
    return TextDiff(ops)


## Tests

_short_text1 = dedent(
    """
    Paragraph one. Sentence 1a. Sentence 1b. Sentence 1c.
    
    Paragraph two. Sentence 2a. Sentence 2b. Sentence 2c.
    
    Paragraph three. Sentence 3a. Sentence 3b. Sentence 3c.
    """
).strip()


_short_text2 = dedent(
    """
    Paragraph one. Sentence 1a. Sentence 1b. Sentence 1c.
    Paragraph two blah. Sentence 2a. Sentence 2b. Sentence 2c.
    
    Paragraph three! Sentence 3a. Sentence 3b.
    """
).strip()


def test_lcs_diff_wordtoks():
    wordtoks1 = list(TextDoc.from_text(_short_text1).as_wordtoks())
    wordtoks2 = list(TextDoc.from_text(_short_text2).as_wordtoks())

    diff = lcs_diff_wordtoks(wordtoks1, wordtoks2)

    print("---Diff:")
    print(diff)

    print("---Diff stats:")
    print(diff.stats())
    assert diff.stats() == TokenDiffStats(added=4, removed=7)

    assert diff.ops[1] == DiffOp(DiffTag.DELETE, ["<-PARA-BR->"])
    assert diff.ops[-1] == DiffOp(DiffTag.DELETE, ["<-SENT-BR->", "Sentence", " ", "3c", "."])

    print("---Non-para breaks:")
    print(diff_non_br_whitespace(diff))

    assert diff_non_br_whitespace(diff) == TextDiff(
        ops=[
            DiffOp(action=DiffTag.INSERT, wordtoks=["blah"]),
            DiffOp(action=DiffTag.DELETE, wordtoks=["."]),
            DiffOp(action=DiffTag.INSERT, wordtoks=["!"]),
            DiffOp(action=DiffTag.DELETE, wordtoks=["Sentence", "3c", "."]),
        ]
    )

    print("---Non-punctuation/whitespace:")
    print(diff_non_punctuation_whitespace(diff))

    assert diff_non_punctuation_whitespace(diff) == TextDiff(
        ops=[
            DiffOp(action=DiffTag.INSERT, wordtoks=["blah"]),
            DiffOp(action=DiffTag.DELETE, wordtoks=["Sentence", "3c"]),
        ]
    )


def test_find_best_alignment():
    wordtoks1 = list(TextDoc.from_text(_short_text1).as_wordtoks())
    wordtoks2 = list(TextDoc.from_text(_short_text1).sub_doc(DocIndex(1, 1)).as_wordtoks())
    wordtoks3 = list(wordtoks2) + ["Extra", "wordtoks", "at", "the", "end"]
    wordtoks4 = list(wordtoks3)
    wordtoks4[0] = "X"
    wordtoks4[3] = "Y"

    print("---Alignment:")
    offset, score, diff = find_best_alignment(wordtoks1, wordtoks2, 1)
    print(f"Offset: {offset}, Score: {score}")
    print(diff)
    print()
    assert offset == 25
    assert score == 0.0
    assert diff.changes() == []

    offset, score, diff = find_best_alignment(wordtoks1, wordtoks3, 3)
    print(f"Offset: {offset}, Score: {score}")
    print(diff)
    print()
    assert offset == 25
    assert score == 0.0
    assert diff.changes() == []

    offset, score, diff = find_best_alignment(wordtoks1, wordtoks4, 3)
    print(f"Offset: {offset}, Score: {score}")
    print(diff)
    print()
    assert offset == 25
    assert score > 0 and score < 0.2
    assert diff.stats().nchanges() == 4
