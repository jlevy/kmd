from typing import Callable, List, Optional

from kmd.text_docs.text_diffs import DiffFilter, DiffOp, OpType

from kmd.text_docs.text_doc import TextDoc
from kmd.text_docs.wordtoks import is_break_or_space, is_tag_close, is_tag_open, is_word


class WildcardToken:
    """
    Wildcard token that matches any number of tokens (including zero).
    """

    def __str__(self):
        return "*"


WILDCARD_TOK = WildcardToken()

TokenMatcher = List[str] | Callable[[str], bool]

TokenPattern = str | Callable[[str], bool] | WildcardToken


def _matches_pattern(tokens: List[str], pattern: List[TokenPattern]) -> bool:
    def match_from(i: int, j: int) -> bool:
        while i <= len(tokens) and j < len(pattern):
            pattern_elem = pattern[j]
            if pattern_elem == WILDCARD_TOK:
                # If '*' is the last pattern element, it matches any remaining tokens.
                if j + 1 == len(pattern):
                    return True
                # Advance pattern index to next pattern after ANY_TOKEN.
                j += 1
                while i < len(tokens):
                    if match_from(i, j):
                        return True
                    i += 1
                return False
            else:
                if i >= len(tokens):
                    return False
                token = tokens[i]
                if isinstance(pattern_elem, str):
                    if token != pattern_elem:
                        return False
                elif callable(pattern_elem):
                    if not pattern_elem(token):
                        return False
                else:
                    return False
                i += 1
                j += 1
        # Skip any remaining ANY_TOKEN in the pattern.
        while j < len(pattern) and pattern[j] == WILDCARD_TOK:
            j += 1
        # The tokens match the pattern if both indices are at the end.
        return i == len(tokens) and j == len(pattern)

    return match_from(0, 0)


def make_token_sequence_filter(
    pattern: List[TokenPattern],
    action: Optional[OpType] = None,
    ignore: Optional[TokenMatcher] = None,
) -> DiffFilter:
    """
    Returns a DiffFilter that accepts DiffOps where the tokens match the given pattern.
    The pattern is a list where each element can be a string or a predicate function that
    takes a token and returns a bool (True if the token matches).
    The '*' in the pattern list matches any number of tokens (including zero).
    If `action` is specified, only DiffOps with that action are considered.
    """

    def filter_fn(diff_op: DiffOp) -> bool:
        if action and diff_op.action != action:
            return False

        tokens = diff_op.all_changed()
        if ignore and isinstance(ignore, str):
            tokens = [tok for tok in tokens if tok not in ignore]
        elif ignore and callable(ignore):
            tokens = [tok for tok in tokens if not ignore(tok)]

        return _matches_pattern(tokens, pattern)

    return filter_fn


def adds_or_removes_whitespace(diff_op: DiffOp) -> bool:
    """
    Only accepts changes to sentence and paragraph breaks and whitespace.
    """

    return all(is_break_or_space(tok) for tok in diff_op.all_changed())


def adds_or_removes_punct_whitespace(diff_op: DiffOp) -> bool:
    """
    Only accepts changes to punctuation and whitespace.
    """

    return all(not is_word(tok) for tok in diff_op.all_changed())


def adds_headings(diff_op: DiffOp) -> bool:
    """
    Only accept changes that add contents within header tags.
    """
    headers = ["h1", "h2", "h3", "h4", "h5", "h6"]
    is_header = lambda tok: is_tag_open(tok, tag_names=headers)
    is_header_close = lambda tok: is_tag_close(tok, tag_names=headers)
    matcher = make_token_sequence_filter(
        [is_header, WILDCARD_TOK, is_header_close],
        action=OpType.INSERT,
        ignore=is_break_or_space,
    )
    return matcher(diff_op)


def accept_all(diff_op: DiffOp) -> bool:
    """
    Accepts all changes.
    """

    return True


## Tests


def test_filter_br_and_space():
    from kmd.text_docs.text_diffs import _short_text1, _short_text2, _short_text3, diff_wordtoks

    wordtoks1 = list(TextDoc.from_text(_short_text1).as_wordtoks())
    wordtoks2 = list(TextDoc.from_text(_short_text2).as_wordtoks())
    wordtoks3 = list(TextDoc.from_text(_short_text3).as_wordtoks())

    diff = diff_wordtoks(wordtoks1, wordtoks2)

    accepted, rejected = diff.filter(adds_or_removes_whitespace)

    accepted_result = accepted.apply_to(wordtoks1)
    rejected_result = rejected.apply_to(wordtoks1)

    print("---Filtered diff:")
    print("Original: " + "/".join(wordtoks1))
    print("Full diff:", diff)
    print("Accepted diff:", accepted)
    print("Rejected diff:", rejected)
    print("Accepted result: " + "/".join(accepted_result))
    print("Rejected result: " + "/".join(rejected_result))

    assert accepted_result == wordtoks3


def test_token_sequence_filter_with_predicate():
    from kmd.text_docs.wordtoks import is_break_or_space, PARA_BR_TOK, SENT_BR_TOK

    insert_op = DiffOp(OpType.INSERT, [], [SENT_BR_TOK, "<h1>", "Title", "</h1>", PARA_BR_TOK])
    delete_op = DiffOp(OpType.DELETE, [SENT_BR_TOK, "<h1>", "Old Title", "</h1>", PARA_BR_TOK], [])
    replace_op = DiffOp(OpType.REPLACE, ["Some", "text"], ["New", "text"])
    equal_op = DiffOp(OpType.EQUAL, ["Unchanged"], ["Unchanged"])

    action = OpType.INSERT
    filter_fn = make_token_sequence_filter(
        [is_break_or_space, "<h1>", WILDCARD_TOK, "</h1>", is_break_or_space], action
    )

    assert filter_fn(insert_op) == True
    assert filter_fn(delete_op) == False  # action is INSERT
    assert filter_fn(replace_op) == False
    assert filter_fn(equal_op) == False

    ignore_whitespace_filter_fn = make_token_sequence_filter(
        ["<h1>", WILDCARD_TOK, "</h1>"],
        action=OpType.INSERT,
        ignore=is_break_or_space,
    )

    insert_op_with_whitespace = DiffOp(
        OpType.INSERT, [], [" ", SENT_BR_TOK, " ", "<h1>", "Title", "</h1>", " ", PARA_BR_TOK, " "]
    )

    assert ignore_whitespace_filter_fn(insert_op_with_whitespace) == True
    assert ignore_whitespace_filter_fn(delete_op) == False  # action is INSERT
    assert ignore_whitespace_filter_fn(replace_op) == False
    assert ignore_whitespace_filter_fn(equal_op) == False