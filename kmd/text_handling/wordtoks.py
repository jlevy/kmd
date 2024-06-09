"""
Support for treating text as a sequence of word, punctuation, or whitespace
word tokens ("wordtoks").
"""

from typing import List
import regex

SENT_BR_TOK = "<-SENT-BR->"
PARA_BR_TOK = "<-PARA-BR->"

SENT_BR_STR = " "
PARA_BR_STR = "\n\n"

SPACE_TOK = " "

# Currently break on words, spaces, or any single other/punctuation character.
# HTML tags (of length <1024 chars) are also a single token.
# TODO: Could add nicer support for Markdown formatting as well.
_wordtok_pattern = regex.compile(r"(<.{0,1024}?>|\w+|[^\w\s]|[\s]+)")

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
    return wordtok


def wordtok_len(wordtok: str) -> int:
    """
    Char length of a wordtok.
    """
    return len(wordtok_to_str(wordtok))


def sentence_as_wordtoks(sentence: str) -> List[str]:
    """
    Break a sentence into word tokens, including words, whitespace, and punctuation.
    Normalizes whitespace to a single space character.
    """
    wordtoks = _wordtok_pattern.findall(sentence)
    wordtoks = [wordtok if not wordtok.isspace() else SPACE_TOK for wordtok in wordtoks]
    return wordtoks


def join_wordtoks(wordtoks: List[str]) -> str:
    """
    Join wordtoks back into a sentence.
    """
    wordtoks = [wordtok_to_str(wordtok) for wordtok in wordtoks]
    return "".join(wordtoks)


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
