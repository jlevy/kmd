from typing import List
import regex

SENT_BR_TOK = "<-SENT-BR->"
PARA_BR_TOK = "<-PARA-BR->"

SENT_BR_STR = " "
PARA_BR_STR = "\n\n"

SPACE_TOK = " "

_token_pattern = regex.compile(r"(\w+|[^\w\s]|[\s]+)")


def tokenize_sentence(sentence: str) -> List[str]:
    """
    Break a sentence into tokens, including words, whitespace, and punctuation.
    Normalizes whitespace to a single space character.
    """
    tokens = _token_pattern.findall(sentence)
    tokens = [token if not token.isspace() else SPACE_TOK for token in tokens]
    return tokens


def join_tokens(tokens: List[str]) -> str:
    """
    Join tokens back into a sentence.
    """
    tokens = [SENT_BR_STR if token == SENT_BR_TOK else token for token in tokens]
    tokens = [PARA_BR_STR if token == PARA_BR_TOK else token for token in tokens]

    return "".join(tokens)


def is_br_space(token: str) -> bool:
    """
    Any kind of paragraph break, sentence break, or space.
    """
    return token == PARA_BR_TOK or token == SENT_BR_TOK or token.isspace()


_word_pat = regex.compile(r"\w+")


def is_word(token: str) -> bool:
    """
    Is this token a word, not punctuation or whitespace?
    """
    return bool(_word_pat.match(token))


## Tests


def test_tokenization():
    test_cases = [
        "Hello, world!",
        "This is an example sentence with punctuation.",
        "And here's another one!",
        "Special characters: @#%^&*()",
    ]

    for sentence in test_cases:
        tokens = tokenize_sentence(sentence)
        reassembled_sentence = "".join(tokens)
        assert reassembled_sentence == sentence

    assert tokenize_sentence("Multiple     spaces and tabs\tand\nnewlines in between.") == [
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
    assert tokenize_sentence("") == []
    assert tokenize_sentence("   ") == [" "]
