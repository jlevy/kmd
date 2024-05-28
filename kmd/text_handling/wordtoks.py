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
# TODO: Could add proper support for Markdown and HTML formatting as wordtoks.
_wordtok_pattern = regex.compile(r"(\w+|[^\w\s]|[\s]+)")


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
    wordtoks = [SENT_BR_STR if wordtok == SENT_BR_TOK else wordtok for wordtok in wordtoks]
    wordtoks = [PARA_BR_STR if wordtok == PARA_BR_TOK else wordtok for wordtok in wordtoks]

    return "".join(wordtoks)


def is_br_or_space(wordtok: str) -> bool:
    """
    Any kind of paragraph break, sentence break, or space.
    """
    return wordtok == PARA_BR_TOK or wordtok == SENT_BR_TOK or wordtok.isspace()


_word_pat = regex.compile(r"\w+")


def is_word(wordtok: str) -> bool:
    """
    Is this wordtok a word, not punctuation or whitespace?
    """
    return bool(_word_pat.match(wordtok))


## Tests


def test_wordtokization():
    test_cases = [
        "Hello, world!",
        "This is an example sentence with punctuation.",
        "And here's another one!",
        "Special characters: @#%^&*()",
    ]

    for sentence in test_cases:
        wordtoks = sentence_as_wordtoks(sentence)
        reassembled_sentence = "".join(wordtoks)
        assert reassembled_sentence == sentence

    assert sentence_as_wordtoks("Multiple     spaces and tabs\tand\nnewlines in between.") == [
        "Multiple",
        " ",
        "spaces",
        " ",
        "and",
        " ",
        "tabs",
        " ",
        "and",
        " ",
        "newlines",
        " ",
        "in",
        " ",
        "between",
        ".",
    ]
    assert sentence_as_wordtoks("") == []
    assert sentence_as_wordtoks("   ") == [" "]
