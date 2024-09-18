"""
Support for treating text as a sequence of word, punctuation, or whitespace
word tokens ("wordtoks").
"""

from textwrap import dedent
from typing import List, Tuple

import regex

from kmd.config.text_styles import SYMBOL_SEP
from kmd.text_docs.search_tokens import search_tokens

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
# HTML tags (of length <1024 chars, possibly with newlines) are also a single token.
# TODO: Could add nicer support for Markdown formatting as well.
_wordtok_pattern = regex.compile(r"(<(?:[^<>]|\n){0,1024}>|\w+|[^\w\s]|\s+)", regex.DOTALL)

_para_br_pattern = regex.compile(r"\s*\n\n\s*")

_tag_pattern = regex.compile(r"<.{0,1024}?>")

_tag_close_pattern = regex.compile(r"</[^>]+>")

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


_whitespace = regex.compile(r"\s+")


def normalize_wordtok(wordtok: str) -> str:
    if wordtok.isspace():
        normalized = SPACE_TOK
    elif wordtok.startswith("<"):
        normalized = _whitespace.sub(" ", wordtok)
    else:
        normalized = wordtok
    return normalized


def raw_text_to_wordtok_offsets(text: str, bof_eof=False) -> Tuple[List[str], List[int]]:
    """
    Same as `raw_text_to_wordtoks`, but returns a list of tuples `(wordtok, offset)`.
    """
    wordtoks = []
    offsets = []
    offset = 0
    for match in _wordtok_pattern.finditer(text):
        wordtok = normalize_wordtok(match.group())
        wordtoks.append(wordtok)
        offsets.append(offset)
        offset = match.end()

    if bof_eof:
        wordtoks = [BOF_TOK] + wordtoks + [EOF_TOK]
        offsets = [0] + offsets + [len(text)]

    return wordtoks, offsets


def raw_text_to_wordtoks(text: str, bof_eof=False) -> List[str]:
    """
    Convert text to word tokens, including words, whitespace, punctuation, and
    HTML tags. Does not parse paragraph orsentence breaks. Normalizes all
    whitespace to a single space character.
    """
    wordtoks, _offsets = raw_text_to_wordtok_offsets(text, bof_eof)
    return wordtoks


def insert_para_wordtoks(text: str) -> str:
    """
    Replace paragraph breaks in text with para break tokens.
    """
    return _para_br_pattern.sub(PARA_BR_TOK, text)


def _initial_wordtoks(text: str, max_chars: int) -> List[str]:
    sub_text = text[:max_chars]
    wordtoks = raw_text_to_wordtoks(sub_text)
    if wordtoks:
        wordtoks.pop()  # Drop any cut off token.
    return wordtoks


def first_wordtok_is_div(text: str) -> bool:
    wordtoks = _initial_wordtoks(text, 100)
    return bool(wordtoks and is_tag(wordtoks[0]) and wordtoks[0].find("<div") >= 0)


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


def is_tag_close(wordtok: str) -> bool:
    """
    Is this wordtok an HTML tag close?
    """
    return bool(_tag_close_pattern.match(wordtok))


## Tests

_test_doc = dedent(
    """
    Hello, world!
    This is an "example sentence with punctuation.
    "Special characters: @#%^&*()"
    <span data-timestamp="5.60">Alright, guys.</span>

    <span data-timestamp="6.16">Here's the deal.</span>
    <span data-timestamp="7.92">You can follow me on my daily workouts.
    <span class="citation timestamp-link" data-src="resources/the_time_is_now.resource.yml"
    data-timestamp="10.29"><a
    href="https://www.youtube.com/">00:10</a></span>
    """
).strip()


def test_html_doc():
    wordtoks = raw_text_to_wordtoks(_test_doc, bof_eof=True)

    print("\n---Wordtoks test:")
    print(visualize_wordtoks(wordtoks))

    print("\n---Wordtoks with para br:")
    wordtoks_with_para = raw_text_to_wordtoks(insert_para_wordtoks(_test_doc), bof_eof=True)
    print(visualize_wordtoks(wordtoks_with_para))

    assert (
        visualize_wordtoks(wordtoks)
        == """⎪<-BOF->⎪Hello⎪,⎪ ⎪world⎪!⎪ ⎪This⎪ ⎪is⎪ ⎪an⎪ ⎪"⎪example⎪ ⎪sentence⎪ ⎪with⎪ ⎪punctuation⎪.⎪ ⎪"⎪Special⎪ ⎪characters⎪:⎪ ⎪@⎪#⎪%⎪^⎪&⎪*⎪(⎪)⎪"⎪ ⎪<span data-timestamp="5.60">⎪Alright⎪,⎪ ⎪guys⎪.⎪</span>⎪ ⎪<span data-timestamp="6.16">⎪Here⎪'⎪s⎪ ⎪the⎪ ⎪deal⎪.⎪</span>⎪ ⎪<span data-timestamp="7.92">⎪You⎪ ⎪can⎪ ⎪follow⎪ ⎪me⎪ ⎪on⎪ ⎪my⎪ ⎪daily⎪ ⎪workouts⎪.⎪ ⎪<span class="citation timestamp-link" data-src="resources/the_time_is_now.resource.yml" data-timestamp="10.29">⎪<a href="https://www.youtube.com/">⎪00⎪:⎪10⎪</a>⎪</span>⎪<-EOF->⎪"""
    )

    assert (
        visualize_wordtoks(wordtoks_with_para)
        == """⎪<-BOF->⎪Hello⎪,⎪ ⎪world⎪!⎪ ⎪This⎪ ⎪is⎪ ⎪an⎪ ⎪"⎪example⎪ ⎪sentence⎪ ⎪with⎪ ⎪punctuation⎪.⎪ ⎪"⎪Special⎪ ⎪characters⎪:⎪ ⎪@⎪#⎪%⎪^⎪&⎪*⎪(⎪)⎪"⎪ ⎪<span data-timestamp="5.60">⎪Alright⎪,⎪ ⎪guys⎪.⎪</span>⎪<-PARA-BR->⎪<span data-timestamp="6.16">⎪Here⎪'⎪s⎪ ⎪the⎪ ⎪deal⎪.⎪</span>⎪ ⎪<span data-timestamp="7.92">⎪You⎪ ⎪can⎪ ⎪follow⎪ ⎪me⎪ ⎪on⎪ ⎪my⎪ ⎪daily⎪ ⎪workouts⎪.⎪ ⎪<span class="citation timestamp-link" data-src="resources/the_time_is_now.resource.yml" data-timestamp="10.29">⎪<a href="https://www.youtube.com/">⎪00⎪:⎪10⎪</a>⎪</span>⎪<-EOF->⎪"""
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
