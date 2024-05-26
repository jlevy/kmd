from dataclasses import dataclass
import difflib
from enum import Enum
from textwrap import dedent
from typing import Callable, List
from kmd.text_handling.text_doc import TextDoc
from kmd.text_handling.text_tokens import is_br_space, is_word


class DiffTag(Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"

    def as_plus_minus(self):
        return "+" if self == DiffTag.INSERT else "-" if self == DiffTag.DELETE else " "


@dataclass
class DiffOp:
    action: DiffTag
    tokens: List[str]

    def filter(self, pred: Callable[[str], bool]):
        return DiffOp(self.action, [tok for tok in self.tokens if pred(tok)])

    def __str__(self):
        if self.tokens:
            return f"{self.action.as_plus_minus()} {", ".join(repr(tok) for tok in self.tokens)},"
        else:
            return "(empty DiffOp)"


@dataclass
class TextDiff:
    """
    A diff of two texts as a sequence of EQUAL, INSERT, and DELETE operations.
    """

    ops: List[DiffOp]

    def changes(self) -> List[DiffOp]:
        return [op for op in self.ops if op.action != DiffTag.EQUAL]

    def __str__(self):
        return "\n".join(str(op) for op in self.ops)


def diff_non_br_whitespace(diff: TextDiff) -> TextDiff:
    """
    Return any diff operations that are not simply changes to whitespace and paragraph breaks.
    """
    ops = []
    for op in diff.changes():
        match = op.filter(lambda tok: not is_br_space(tok))
        if len(match.tokens) > 0:
            ops.append(match)
    return TextDiff(ops)


def diff_non_punctuation_whitespace(diff: TextDiff) -> TextDiff:
    """
    Return any diff operations that are not simply changes to punctuation or whitespace.
    """
    ops = []
    for op in diff.changes():
        match = op.filter(lambda tok: bool(is_word(tok)))
        if len(match.tokens) > 0:
            ops.append(match)
    return TextDiff(ops)


def lcs_diff_tokens(tokens1: List[str], tokens2: List[str]) -> TextDiff:
    """
    Perform an LCS-style diff on two lists of tokens.
    """
    s = difflib.SequenceMatcher(None, tokens1, tokens2)
    diff: List[DiffOp] = []

    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == "equal":
            diff.append(DiffOp(DiffTag.EQUAL, tokens1[i1:i2]))
        elif tag == "insert":
            diff.append(DiffOp(DiffTag.INSERT, tokens2[j1:j2]))
        elif tag == "delete":
            diff.append(DiffOp(DiffTag.DELETE, tokens1[i1:i2]))
        elif tag == "replace":
            diff.append(DiffOp(DiffTag.DELETE, tokens1[i1:i2]))
            diff.append(DiffOp(DiffTag.INSERT, tokens2[j1:j2]))

    return TextDiff(diff)


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


def test_lcs_diff_tokens():

    diff = lcs_diff_tokens(
        TextDoc.from_text(_short_text1).as_tokens(), TextDoc.from_text(_short_text2).as_tokens()
    )

    print("---Diff:")
    print(diff)

    assert diff.ops[1] == DiffOp(DiffTag.DELETE, ["<-PARA-BR->"])
    assert diff.ops[-1] == DiffOp(DiffTag.DELETE, ["<-SENT-BR->", "Sentence", " ", "3c", "."])

    print("---Non-para breaks:")
    print(diff_non_br_whitespace(diff))

    assert diff_non_br_whitespace(diff) == TextDiff(
        ops=[
            DiffOp(action=DiffTag.INSERT, tokens=["blah"]),
            DiffOp(action=DiffTag.DELETE, tokens=["."]),
            DiffOp(action=DiffTag.INSERT, tokens=["!"]),
            DiffOp(action=DiffTag.DELETE, tokens=["Sentence", "3c", "."]),
        ]
    )

    print("---Non-punctuation/whitespace:")
    print(diff_non_punctuation_whitespace(diff))

    assert diff_non_punctuation_whitespace(diff) == TextDiff(
        ops=[
            DiffOp(action=DiffTag.INSERT, tokens=["blah"]),
            DiffOp(action=DiffTag.DELETE, tokens=["Sentence", "3c"]),
        ]
    )
