from typing import List, Tuple

Insertion = Tuple[int, str]


def insert_multiple(text: str, insertions: List[Insertion]) -> str:
    """
    Insert multiple strings into `text` at the given offsets.
    """
    chunks = []
    last_end = 0
    for offset, insertion in sorted(insertions, key=lambda x: x[0]):
        chunks.append(text[last_end:offset])
        chunks.append(insertion)
        last_end = offset
    chunks.append(text[last_end:])
    return "".join(chunks)


## Tests


def test_insert_multiple():
    text = "hello world"
    insertions = [(5, ",")]
    expected = "hello, world"
    assert insert_multiple(text, insertions) == expected, "Single insertion failed"

    text = "hello world"
    insertions = [(0, "Start "), (11, " End")]
    expected = "Start hello world End"
    assert insert_multiple(text, insertions) == expected, "Multiple insertions failed"

    text = "short"
    insertions = [(10, " end")]
    expected = "short end"
    assert insert_multiple(text, insertions) == expected, "Out of bounds insertion failed"

    text = "negative test"
    insertions = [(-1, "ss")]
    expected = "negative tessst"
    assert insert_multiple(text, insertions) == expected, "Negative offset insertion failed"

    text = "no change"
    insertions = []
    expected = "no change"
    assert insert_multiple(text, insertions) == expected, "Empty insertions failed"
