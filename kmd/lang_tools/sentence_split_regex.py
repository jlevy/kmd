from typing import Callable, List

import regex


# These heuristics are from Flowmark:
# https://github.com/jlevy/atom-flowmark/blob/master/lib/remark-smart-word-wrap.js#L17-L33

# They work pretty well when used for formatting and editing documents in English.
# Note this is smarter than Python textwrap's simple heuristic:
# https://github.com/python/cpython/blob/main/Lib/textwrap.py#L105-L110

# Heuristic: End of sentence must be two letters or more, with the last letter lowercase,
# followed by a period, exclamation point, question mark, colon, or semicolon.
# Except for colon or semicolon, a final or preceding parenthesis or quote is allowed.
# XXX: Could also handle rare cases with both quotes and parentheses at sentence end
# but may not be worth it. Also does not detect sentences ending in numerals, which
# tends to cause too many false positives. Should be OK for most Latin languages but
# may need to rethink the 2-letter restriction for some languages.
SENTENCE_RE = regex.compile(r"(\p{L}[\p{Ll}])([.?!]['\"’”)]?|['\"’”)][.?!]|[:;]) *$")

# Second heuristic: Very short sentences often not so useful.
SENTENCE_MIN_LENGTH = 15


def heuristic_end_of_sentence(word: str) -> bool:
    return bool(SENTENCE_RE.search(word))


def split_sentences_regex(
    text: str,
    heuristic: Callable[[str], bool] = heuristic_end_of_sentence,
    min_length: int = SENTENCE_MIN_LENGTH,
) -> List[str]:
    """
    Split text into sentences using an approximate, fast regex heuristic. (English.)
    Goal is to be conservative, not perfect, avoiding excessive breaks.
    """
    words = text.split()
    sentences = []
    sentence = []
    words_len = 0
    for word in words:
        sentence.append(word)
        words_len += len(word)
        sentence_len = words_len + len(sentence) - 1
        if heuristic(word) and sentence_len >= min_length:
            sentences.append(" ".join(sentence))
            sentence = []
            words_len = 0
    if sentence:
        sentences.append(" ".join(sentence))
    return sentences
