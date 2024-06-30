"""
Support for treating text as a sequence of word, punctuation, or whitespace
word tokens ("wordtoks").
"""

from textwrap import dedent
from typing import List, Callable, Union
import regex
from kmd.text_ui.text_styles import SYMBOL_SEP

# Note these parse as tokens and like HTML tags, so they can safely be mixed into inputs if desired.
SENT_BR_TOK = "<-SENT-BR->"
PARA_BR_TOK = "<-PARA-BR->"
BOF_TOK = "<-BOF->"
EOF_TOK = "<-EOF->"

SENT_BR_STR = " "
PARA_BR_STR = "\n\n"
BOF_STR = ""
EOF_STR = ""

SPACE_TOK = " "

# Currently break on words, spaces, or any single other/punctuation character.
# HTML tags (of length <1024 chars) are also a single token.
# TODO: Could add nicer support for Markdown formatting as well.
_wordtok_pattern = regex.compile(r"(<.{0,1024}?>|\w+|[^\w\s]|\s+)")

_para_br_pattern = regex.compile(r"\s*\n\n\s*")

_tag_pattern = regex.compile(r"<.{0,1024}?>")

_word_pat = regex.compile(r"\w+")


def wordtok_to_str(wordtok: str) -> str:
    """
    Convert a wordtok to a string.
    """
    if wordtok == SENT_BR_TOK:
        return SENT_BR_STR
    if wordtok == PARA_BR_TOK:
        return PARA_BR_STR
    if wordtok == BOF_TOK:
        return BOF_STR
    if wordtok == EOF_TOK:
        return EOF_STR
    return wordtok


def wordtok_len(wordtok: str) -> int:
    """
    Char length of a wordtok.
    """
    return len(wordtok_to_str(wordtok))


def raw_text_to_wordtoks(text: str, parse_para_br=False, bof_eof=False) -> List[str]:
    """
    Fast breaking of text into word tokens, including words, whitespace, and punctuation.
    Does not look for paragraph breaks unless `parse_para_br` is True. Does not parse
    sentence breaks. Normalizes all other whitespace to a single space character.
    """
    if parse_para_br:
        text = _para_br_pattern.sub(PARA_BR_TOK, text)

    wordtoks = _wordtok_pattern.findall(text)
    wordtoks = [wordtok if not wordtok.isspace() else SPACE_TOK for wordtok in wordtoks]

    if bof_eof:
        return [BOF_TOK, *wordtoks, EOF_TOK]
    else:
        return wordtoks


def join_wordtoks(wordtoks: List[str]) -> str:
    """
    Join wordtoks back into a sentence.
    """
    wordtoks = [wordtok_to_str(wordtok) for wordtok in wordtoks]
    return "".join(wordtoks)


def visualize_wordtoks(wordtoks: List[str]) -> str:
    """
    Visualize wordtoks for debugging.
    """
    return SYMBOL_SEP + SYMBOL_SEP.join(wordtoks) + SYMBOL_SEP


def is_break_or_space(wordtok: str) -> bool:
    """
    Any kind of paragraph break, sentence break, or space.
    """
    return wordtok == PARA_BR_TOK or wordtok == SENT_BR_TOK or wordtok.isspace()


def is_word(wordtok: str) -> bool:
    """
    Is this wordtok a word, not punctuation or whitespace?
    """
    return bool(_word_pat.match(wordtok))


def is_tag(wordtok: str) -> bool:
    """
    Is this wordtok an HTML tag?
    """
    return bool(_tag_pattern.match(wordtok))


Predicate = Union[Callable[[str], bool], List[str]]


class _TokenSearcher:
    def __init__(self, wordtoks: List[str]):
        self.wordtoks = wordtoks
        self.current_idx = 0

    def at(self, index: int):
        if index is None:
            raise KeyError("Index cannot be None")
        # Convert negative indices to positive ones.
        self.current_idx = index if index >= 0 else len(self.wordtoks) + index
        return self

    def seek_back(self, predicate: Predicate):
        if isinstance(predicate, list):
            allowed: List[str] = predicate
            predicate = lambda x: x in allowed
        for idx in range(self.current_idx - 1, -1, -1):
            if predicate(self.wordtoks[idx]):
                self.current_idx = idx
                return self
        raise KeyError("No matching token found before the current index")

    def seek_forward(self, predicate: Predicate):
        if isinstance(predicate, list):
            allowed: List[str] = predicate
            predicate = lambda x: x in allowed
        for idx in range(self.current_idx + 1, len(self.wordtoks)):
            if predicate(self.wordtoks[idx]):
                self.current_idx = idx
                return self
        raise KeyError("No matching token found after the current index")

    def prev(self):
        if self.current_idx - 1 < 0:
            raise KeyError("No previous token available")
        self.current_idx -= 1
        return self

    def next(self):
        if self.current_idx + 1 >= len(self.wordtoks):
            raise KeyError("No next token available")
        self.current_idx += 1
        return self

    def get_index(self):
        return self.current_idx

    def get_token(self):
        return self.current_idx, self.wordtoks[self.current_idx]


def search_tokens(wordtoks: List[str]) -> _TokenSearcher:
    """
    Convenience function to search for offsets in an array of tokens.
    """
    return _TokenSearcher(wordtoks)


## Tests

_test_doc = dedent(
    """
    Hello, world!
    This is an "example sentence with punctuation.
    "Special characters: @#%^&*()"
    <span data-timestamp="5.60">Alright, guys.</span>

    <span data-timestamp="6.16">Here's the deal.</span>
    <span data-timestamp="7.92">You can follow me on my daily workouts.
    """
).strip()


def test_html_doc():
    wordtoks = raw_text_to_wordtoks(_test_doc, bof_eof=True)

    print("\n---Wordtoks test:")
    print(visualize_wordtoks(wordtoks))

    wordtoks_with_para = raw_text_to_wordtoks(_test_doc, parse_para_br=True, bof_eof=True)
    print(visualize_wordtoks(wordtoks_with_para))

    assert (
        visualize_wordtoks(wordtoks)
        == """⎪<-BOF->⎪Hello⎪,⎪ ⎪world⎪!⎪ ⎪This⎪ ⎪is⎪ ⎪an⎪ ⎪"⎪example⎪ ⎪sentence⎪ ⎪with⎪ ⎪punctuation⎪.⎪ ⎪"⎪Special⎪ ⎪characters⎪:⎪ ⎪@⎪#⎪%⎪^⎪&⎪*⎪(⎪)⎪"⎪ ⎪<span data-timestamp="5.60">⎪Alright⎪,⎪ ⎪guys⎪.⎪</span>⎪ ⎪<span data-timestamp="6.16">⎪Here⎪'⎪s⎪ ⎪the⎪ ⎪deal⎪.⎪</span>⎪ ⎪<span data-timestamp="7.92">⎪You⎪ ⎪can⎪ ⎪follow⎪ ⎪me⎪ ⎪on⎪ ⎪my⎪ ⎪daily⎪ ⎪workouts⎪.⎪<-EOF->⎪"""
    )

    assert (
        visualize_wordtoks(wordtoks_with_para)
        == """⎪<-BOF->⎪Hello⎪,⎪ ⎪world⎪!⎪ ⎪This⎪ ⎪is⎪ ⎪an⎪ ⎪"⎪example⎪ ⎪sentence⎪ ⎪with⎪ ⎪punctuation⎪.⎪ ⎪"⎪Special⎪ ⎪characters⎪:⎪ ⎪@⎪#⎪%⎪^⎪&⎪*⎪(⎪)⎪"⎪ ⎪<span data-timestamp="5.60">⎪Alright⎪,⎪ ⎪guys⎪.⎪</span>⎪<-PARA-BR->⎪<span data-timestamp="6.16">⎪Here⎪'⎪s⎪ ⎪the⎪ ⎪deal⎪.⎪</span>⎪ ⎪<span data-timestamp="7.92">⎪You⎪ ⎪can⎪ ⎪follow⎪ ⎪me⎪ ⎪on⎪ ⎪my⎪ ⎪daily⎪ ⎪workouts⎪.⎪<-EOF->⎪"""
    )

    print("\n---Searching tokens")

    print(search_tokens(wordtoks).at(0).seek_forward(["example"]).get_token())
    print(search_tokens(wordtoks).at(-1).seek_back(["follow"]).get_token())
    print(search_tokens(wordtoks).at(-1).seek_back(["Special"]).seek_forward(is_tag).get_token())

    assert search_tokens(wordtoks).at(0).seek_forward(["example"]).get_token() == (14, "example")
    assert search_tokens(wordtoks).at(-1).seek_back(["follow"]).get_token() == (63, "follow")
    assert search_tokens(wordtoks).at(-1).seek_back(["Special"]).seek_forward(
        is_tag
    ).get_token() == (39, '<span data-timestamp="5.60">')
