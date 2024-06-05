from dataclasses import dataclass
import difflib
from enum import Enum
from textwrap import dedent
from typing import Callable, List, Optional, Tuple
from kmd.text_handling.text_doc import DocIndex, TextDoc
from kmd.text_handling.wordtoks import is_break_or_space, is_word


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

    def __str__(self):
        if self.wordtoks:
            return f"{self.action.as_plus_minus()} \"{''.join(tok for tok in self.wordtoks)}\""
        else:
            return "(empty DiffOp)"


@dataclass
class DiffStats:
    added: int
    removed: int

    def nchanges(self) -> int:
        return self.added + self.removed

    def __str__(self):
        return f"+{self.added} added, -{self.removed} removed"


DiffOpFilter = Callable[[DiffOp], bool]

ONLY_BREAKS_AND_SPACES: DiffOpFilter = lambda diff_op: all(
    is_break_or_space(tok) for tok in diff_op.wordtoks
)
"""Only accepts changes to sentence and paragraph breaks and whitespace."""

ONLY_PUNCT_AND_SPACES: DiffOpFilter = lambda diff_op: all(
    not is_word(tok) for tok in diff_op.wordtoks
)
"""Only accepts changes to punctuation and whitespace."""

ALL_CHANGES: DiffOpFilter = lambda diff_op: True
"""Accepts all changes."""


@dataclass
class TextDiff:
    """
    A diff of two texts as a sequence of EQUAL, INSERT, and DELETE operations on wordtoks.
    """

    ops: List[DiffOp]

    def changes(self) -> List[DiffOp]:
        return [op for op in self.ops if op.action != DiffTag.EQUAL]

    def stats(self) -> DiffStats:
        wordtoks_added = sum(len(op.wordtoks) for op in self.ops if op.action == DiffTag.INSERT)
        wordtoks_removed = sum(len(op.wordtoks) for op in self.ops if op.action == DiffTag.DELETE)
        return DiffStats(wordtoks_added, wordtoks_removed)

    def apply_to(self, original_wordtoks: List[str]) -> List[str]:
        """
        Apply the diff to a list of wordtoks.
        """
        result = []
        original_index = 0

        for op in self.ops:
            if op.action == DiffTag.EQUAL:
                result.extend(original_wordtoks[original_index : original_index + len(op.wordtoks)])
                original_index += len(op.wordtoks)
            elif op.action == DiffTag.DELETE:
                original_index += len(op.wordtoks)
            elif op.action == DiffTag.INSERT:
                result.extend(op.wordtoks)

        result.extend(original_wordtoks[original_index:])

        return result

    def filter(self, accept_fn: DiffOpFilter) -> Tuple["TextDiff", "TextDiff"]:
        """
        Return two diffs, one that only applies accepted operations and one that only applies
        rejected operations.
        """
        accepted_ops = []
        rejected_ops = []

        for op in self.ops:
            if op.action == DiffTag.EQUAL:
                # For equal ops, all tokens are both accepted and rejected.
                accepted_ops.append(op)
                rejected_ops.append(op)
            else:
                # We take the DiffOp as a whole, not token by token, since token by token yields odd results,
                # like deleting words but leaving whitespace.
                if accept_fn(op):
                    accepted_ops.append(op)
                    rejected_ops.append(DiffOp(DiffTag.EQUAL, op.wordtoks))
                else:
                    accepted_ops.append(DiffOp(DiffTag.EQUAL, op.wordtoks))
                    rejected_ops.append(op)

        return TextDiff(accepted_ops), TextDiff(rejected_ops)

    def line_summary(self) -> str:
        toks = 0
        lines = []
        for op in self.ops:
            if op.action != DiffTag.EQUAL:
                lines.append(f"at tok {toks:4}: {op}")
            toks += len(op.wordtoks)
        return "\n".join(lines)

    def __str__(self):
        if len(self.changes()) == 0:
            return "TextDiff: No changes"
        else:
            return "TextDiff:\n" + self.line_summary()


def diff_docs(doc1: TextDoc, doc2: TextDoc) -> TextDiff:
    """
    Calculate the LCS-style diff between two documents based on words.
    """
    return diff_wordtoks(doc1.as_wordtoks(), doc2.as_wordtoks())


def diff_wordtoks(wordtoks1: List[str], wordtoks2: List[str]) -> TextDiff:
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


ScoredDiff = Tuple[float, TextDiff]


def scored_diff_wordtoks(wordtoks1: List[str], wordtoks2: List[str]) -> ScoredDiff:
    """
    Calculate the number of wordtoks added and removed between two lists of tokens.
    Score is (wordtoks_added + wordtoks_removed) / min(len(doc1), len(doc2)),
    which is 0 for identical docs.
    """

    if len(wordtoks1) == 0 or len(wordtoks2) == 0:
        raise ValueError("Cannot score diff for empty documents")

    diff = diff_wordtoks(wordtoks1, wordtoks2)
    score = float(diff.stats().nchanges()) / min(len(wordtoks1), len(wordtoks2))
    return score, diff


def find_best_alignment(
    list1: List[str],
    list2: List[str],
    min_overlap: int,
    max_overlap: Optional[int] = None,
    scored_diff: Callable[[List[str], List[str]], ScoredDiff] = scored_diff_wordtoks,
) -> Tuple[int, ScoredDiff]:
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

    return best_offset, (best_score, best_diff)


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

# _short_text3 contains all the whitespace and break-only changes from _short_text1 to _short_text2.
_short_text3 = dedent(
    """
    Paragraph one. Sentence 1a. Sentence 1b. Sentence 1c.
    Paragraph two. Sentence 2a. Sentence 2b. Sentence 2c.
    
    Paragraph three. Sentence 3a. Sentence 3b. Sentence 3c.
    """
).strip()


def test_lcs_diff_wordtoks():
    wordtoks1 = TextDoc.from_text(_short_text1).as_wordtoks()
    wordtoks2 = TextDoc.from_text(_short_text2).as_wordtoks()

    diff = diff_wordtoks(wordtoks1, wordtoks2)

    print("---Diff:")
    print(diff)

    print("---Diff stats:")
    print(diff.stats())
    assert diff.stats() == DiffStats(added=4, removed=7)

    assert diff.ops[1] == DiffOp(DiffTag.DELETE, ["<-PARA-BR->"])
    assert diff.ops[-1] == DiffOp(DiffTag.DELETE, ["<-SENT-BR->", "Sentence", " ", "3c", "."])


def test_apply_to():
    wordtoks1 = list(TextDoc.from_text(_short_text1).as_wordtoks_iter())
    wordtoks2 = list(TextDoc.from_text(_short_text2).as_wordtoks_iter())

    diff = diff_wordtoks(wordtoks1, wordtoks2)
    result = diff.apply_to(wordtoks1)
    print(f"---Applied diff:")
    print("/".join(wordtoks1))
    print(diff)
    print("/".join(result))
    assert result == wordtoks2

    wordtoks3 = ["a", "b", "c", "d", "e"]
    wordtoks4 = ["a", "x", "c", "y", "e"]
    diff2 = diff_wordtoks(wordtoks3, wordtoks4)
    result2 = diff2.apply_to(wordtoks3)
    assert result2 == wordtoks4


def test_filter_br_and_space():
    wordtoks1 = TextDoc.from_text(_short_text1).as_wordtoks()
    wordtoks2 = TextDoc.from_text(_short_text2).as_wordtoks()
    wordtoks3 = TextDoc.from_text(_short_text3).as_wordtoks()

    diff = diff_wordtoks(wordtoks1, wordtoks2)

    accepted, rejected = diff.filter(ONLY_BREAKS_AND_SPACES)

    accepted_result = accepted.apply_to(wordtoks1)
    rejected_result = rejected.apply_to(wordtoks1)

    print(f"---Filtered diff:")
    print("Original: " + "/".join(wordtoks1))
    print("Full diff:", diff)
    print("Accepted diff:", accepted)
    print("Rejected diff:", rejected)
    print("Accepted result: " + "/".join(accepted_result))
    print("Rejected result: " + "/".join(rejected_result))

    assert accepted_result == wordtoks3


def test_find_best_alignment():
    wordtoks1 = TextDoc.from_text(_short_text1).as_wordtoks()
    wordtoks2 = TextDoc.from_text(_short_text1).sub_doc(DocIndex(1, 1)).as_wordtoks()
    wordtoks3 = wordtoks2 + ["Extra", "wordtoks", "at", "the", "end"]
    wordtoks4 = list(wordtoks3)
    wordtoks4[0] = "X"
    wordtoks4[3] = "Y"

    print("---Alignment:")
    offset, (score, diff) = find_best_alignment(wordtoks1, wordtoks2, 1)
    print(f"Offset: {offset}, Score: {score}")
    print(diff)
    print()
    assert offset == 25
    assert score == 0.0
    assert diff.changes() == []

    offset, (score, diff) = find_best_alignment(wordtoks1, wordtoks3, 3)
    print(f"Offset: {offset}, Score: {score}")
    print(diff)
    print()
    assert offset == 25
    assert score == 0.0
    assert diff.changes() == []

    offset, (score, diff) = find_best_alignment(wordtoks1, wordtoks4, 3)
    print(f"Offset: {offset}, Score: {score}")
    print(diff)
    print()
    assert offset == 25
    assert score > 0 and score < 0.2
    assert diff.stats().nchanges() == 4
