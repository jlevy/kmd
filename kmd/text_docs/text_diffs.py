from dataclasses import dataclass
import difflib
from enum import Enum
from textwrap import dedent
from typing import Callable, List, Optional, Tuple
from kmd.config.logger import get_logger
from kmd.config.text_styles import SYMBOL_SEP
from kmd.model.errors_model import UnexpectedError
from kmd.text_docs.text_doc import SentIndex, TextDoc
from kmd.text_docs.wordtoks import is_break_or_space, is_word
from kmd.util.log_calls import log_calls, tally_calls


log = get_logger(__name__)


class DiffTag(Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"

    def as_symbol(self):
        abbrev = {
            DiffTag.EQUAL: " ",
            DiffTag.INSERT: "+",
            DiffTag.DELETE: "-",
            DiffTag.REPLACE: "±",
        }
        return abbrev[self]

    def as_abbrev(self):
        abbrev = {
            DiffTag.EQUAL: "keep",
            DiffTag.INSERT: "add ",
            DiffTag.DELETE: "del ",
            DiffTag.REPLACE: "repl",
        }
        return abbrev[self]


@dataclass(frozen=True)
class DiffOp:
    action: DiffTag
    left: List[str]
    right: List[str]

    def __post_init__(self):
        if self.action == DiffTag.REPLACE:
            assert self.left and self.right
        elif self.action == DiffTag.EQUAL:
            assert self.left == self.right
        elif self.action == DiffTag.INSERT:
            assert not self.left
        elif self.action == DiffTag.DELETE:
            assert not self.right

    def left_str(self, show_toks=True) -> str:
        s = f"{self.action.as_abbrev()} {len(self.left):4} toks"
        if show_toks:
            s += f": - {SYMBOL_SEP}{''.join(tok for tok in self.left)}{SYMBOL_SEP}"
        return s

    def right_str(self, show_toks=True) -> str:
        s = f"{self.action.as_abbrev()} {len(self.right):4} toks"
        if show_toks:
            s += f": + {SYMBOL_SEP}{''.join(tok for tok in self.right)}{SYMBOL_SEP}"
        return s

    def equal_str(self, show_toks=True) -> str:
        s = f"{self.action.as_abbrev()} {len(self.left):4} toks"
        if show_toks:
            s += f":   {SYMBOL_SEP}{''.join(tok for tok in self.left)}{SYMBOL_SEP}"
        return s

    def __str__(self):
        return


@dataclass(frozen=True)
class DiffStats:
    added: int
    removed: int
    input_size: int

    def nchanges(self) -> int:
        return self.added + self.removed

    def __str__(self):
        return f"add/remove +{self.added}/-{self.removed} out of {self.input_size} total"


DiffOpFilter = Callable[[DiffOp], bool]

ONLY_BREAKS_AND_SPACES: DiffOpFilter = lambda diff_op: all(
    is_break_or_space(tok) for tok in diff_op.left + diff_op.right
)
"""Only accepts changes to sentence and paragraph breaks and whitespace."""

ONLY_PUNCT_AND_SPACES: DiffOpFilter = lambda diff_op: all(
    not is_word(tok) for tok in diff_op.left + diff_op.right
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

    def left_size(self) -> int:
        return sum(len(op.left) for op in self.ops)

    def right_size(self) -> int:
        return sum(len(op.right) for op in self.ops)

    def changes(self) -> List[DiffOp]:
        return [op for op in self.ops if op.action != DiffTag.EQUAL]

    def stats(self) -> DiffStats:
        wordtoks_added = sum(len(op.right) for op in self.ops if op.action != DiffTag.EQUAL)
        wordtoks_removed = sum(len(op.left) for op in self.ops if op.action != DiffTag.EQUAL)
        return DiffStats(wordtoks_added, wordtoks_removed, self.left_size())

    def apply_to(self, original_wordtoks: List[str]) -> List[str]:
        """
        Apply a complete diff (including equality ops) to a list of wordtoks.
        """
        result = []
        original_index = 0

        if len(original_wordtoks) != self.left_size():
            raise UnexpectedError(
                f"Diff should be complete: original wordtoks length {len(original_wordtoks)} != diff length {self.left_size()}"
            )

        for op in self.ops:
            if op.left:
                original_index += len(op.left)
            if op.right:
                result.extend(op.right)

        return result

    def filter(self, accept_fn: DiffOpFilter) -> Tuple["TextDiff", "TextDiff"]:
        """
        Return two diffs, one that only has accepted operations and one that only has
        rejected operations.
        """
        accepted_ops, rejected_ops = [], []

        for op in self.ops:
            if op.action == DiffTag.EQUAL:
                # For equal ops, all tokens are both accepted and rejected.
                accepted_ops.append(op)
                rejected_ops.append(op)
            else:
                # We accapt or reject the DiffOp as a whole, not token by token, since token by
                # token would give odd results, like deleting words but leaving whitespace.
                if accept_fn(op):
                    accepted_ops.append(op)
                    rejected_ops.append(DiffOp(DiffTag.EQUAL, op.left, op.left))
                else:
                    accepted_ops.append(DiffOp(DiffTag.EQUAL, op.left, op.left))
                    rejected_ops.append(op)

        assert len(accepted_ops) == len(self.ops)
        assert len(accepted_ops) == len(rejected_ops)

        accepted_diff, rejected_diff = TextDiff(accepted_ops), TextDiff(rejected_ops)

        assert accepted_diff.left_size() == self.left_size()
        assert rejected_diff.left_size() == self.left_size()

        return accepted_diff, rejected_diff

    def _diff_lines(self, include_equal=False) -> List[str]:
        if len(self.ops) == 0:
            return ["(No changes)"]

        pos = 0
        lines = []
        for op in self.ops:
            if op.action == DiffTag.EQUAL:
                if include_equal:
                    lines.append(f"at pos {pos:4} {op.equal_str()}")
            elif op.action == DiffTag.INSERT:
                lines.append(f"at pos {pos:4} {op.right_str()}")
            elif op.action == DiffTag.DELETE:
                lines.append(f"at pos {pos:4} {op.left_str()}")
            elif op.action == DiffTag.REPLACE:
                lines.append(f"at pos {pos:4} {op.left_str()}")
                lines.append(f"       {'':4} {op.right_str()}")

            pos += len(op.left)
        return lines

    def as_diff_str(self, include_equal=True) -> str:
        diff_str = "\n".join(self._diff_lines(include_equal=include_equal))
        return f"TextDiff: {self.stats()}:\n{diff_str}"

    def __str__(self):
        return self.as_diff_str()


def diff_docs(doc1: TextDoc, doc2: TextDoc) -> TextDiff:
    """
    Calculate the LCS-style diff between two documents based on words.
    """

    diff = diff_wordtoks(doc1.as_wordtoks(), doc2.as_wordtoks())

    # log.save_object("doc1 wordtoks", "diff_docs", "\n".join(doc1.as_wordtoks()))
    # log.save_object("doc2 wordtoks", "diff_docs", "\n".join(doc2.as_wordtoks()))
    # log.save_object("diff", "diff_docs", diff)

    return diff


@tally_calls(level="warning", min_total_runtime=5)
def diff_wordtoks(wordtoks1: List[str], wordtoks2: List[str]) -> TextDiff:
    """
    Perform an LCS-style diff on two lists of wordtoks.
    """
    s = difflib.SequenceMatcher(None, wordtoks1, wordtoks2, autojunk=False)
    diff: List[DiffOp] = []

    # log.message(f"Diffing {len(wordtoks1)} wordtoks against {len(wordtoks2)} wordtoks")
    # log.save_object("wordtoks1", "diff_wordtoks", "".join(wordtoks1))
    # log.save_object("wordtoks2", "diff_wordtoks", "".join(wordtoks2))
    # log.save_object("diff opcodes", "diff_wordtoks", "\n".join(str(o) for o in s.get_opcodes()))

    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == "equal":
            slice1 = wordtoks1[i1:i2]
            assert slice1 == wordtoks2[j1:j2]
            diff.append(DiffOp(DiffTag.EQUAL, slice1, slice1))
        elif tag == "insert":
            diff.append(DiffOp(DiffTag.INSERT, [], wordtoks2[j1:j2]))
        elif tag == "delete":
            diff.append(DiffOp(DiffTag.DELETE, wordtoks1[i1:i2], []))
        elif tag == "replace":
            diff.append(DiffOp(DiffTag.REPLACE, wordtoks1[i1:i2], wordtoks2[j1:j2]))

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


@log_calls(level="message", if_slower_than=0.25)
def find_best_alignment(
    list1: List[str],
    list2: List[str],
    min_overlap: int,
    max_overlap: Optional[int] = None,
    scored_diff: Callable[[List[str], List[str]], ScoredDiff] = scored_diff_wordtoks,
    give_up_score: float = 0.75,
    give_up_count: int = 30,
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
            f"Minimum overlap {min_overlap} should never exceed the length of one of the lists ({len1}, {len2})"
        )

    log.message(
        f"Finding best alignment: List lengths: lengths %s and %s with overlap of %s to %s",
        len1,
        len2,
        min_overlap,
        max_overlap,
    )

    # To make this a bit more efficient we check if we have a run of increasing scores and
    # give up if we have many in a row.
    scores_increasing = 0
    prev_score = float("-inf")

    # Slide the second list over the first list, starting from the end of the first list.
    # TODO: This could be much more efficient by being cleverer about reusing diff calculations.s
    for overlap in range(min_overlap, max_overlap + 1):
        start1 = len1 - overlap
        end1 = len1
        start2 = 0
        end2 = overlap

        score, diff = scored_diff(list1[start1:end1], list2[start2:end2])

        log.info("Offset %s: Overlap %s: Score %f", start1, overlap, score)

        if score < best_score:
            best_score = score
            best_offset = start1
            best_diff = diff
            scores_increasing = 0
        elif score >= give_up_score and score >= prev_score:
            scores_increasing += 1
            if scores_increasing >= give_up_count:
                log.info(
                    "Giving up after %s increasing scores, last score %s > %s",
                    give_up_count,
                    score,
                    give_up_score,
                )
                break

        prev_score = score

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
    print(diff.as_diff_str(True))

    print("---Diff stats:")
    print(diff.stats())
    assert diff.stats() == DiffStats(added=4, removed=7, input_size=59)

    expected_diff = dedent(
        """
        TextDiff: add/remove +4/-7 out of 59 total:
        at pos    0 keep   19 toks:   ⎪Paragraph one.<-SENT-BR->Sentence 1a.<-SENT-BR->Sentence 1b.<-SENT-BR->Sentence 1c.⎪
        at pos   19 repl    1 toks: - ⎪<-PARA-BR->⎪
                    repl    1 toks: + ⎪<-SENT-BR->⎪
        at pos   20 keep    3 toks:   ⎪Paragraph two⎪
        at pos   23 add     2 toks: + ⎪ blah⎪
        at pos   23 keep   20 toks:   ⎪.<-SENT-BR->Sentence 2a.<-SENT-BR->Sentence 2b.<-SENT-BR->Sentence 2c.<-PARA-BR->Paragraph three⎪
        at pos   43 repl    1 toks: - ⎪.⎪
                    repl    1 toks: + ⎪!⎪
        at pos   44 keep   10 toks:   ⎪<-SENT-BR->Sentence 3a.<-SENT-BR->Sentence 3b.⎪
        at pos   54 del     5 toks: - ⎪<-SENT-BR->Sentence 3c.⎪
        """
    ).strip()

    assert str(diff.as_diff_str(True)) == expected_diff


def test_apply_to():
    wordtoks1 = TextDoc.from_text(_short_text1).as_wordtoks()
    wordtoks2 = TextDoc.from_text(_short_text2).as_wordtoks()

    diff = diff_wordtoks(wordtoks1, wordtoks2)

    print(f"---Before apply:")
    print("/".join(wordtoks1))
    print(diff)
    result = diff.apply_to(wordtoks1)
    print(f"---Result of apply:")
    print("/".join(result))
    print(f"---Expected:")
    print("/".join(wordtoks2))
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
    wordtoks2 = TextDoc.from_text(_short_text1).sub_doc(SentIndex(1, 1)).as_wordtoks()
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
