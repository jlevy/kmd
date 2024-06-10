"""
Tools for handling documents consisting of sentences and paragraphs of text.
Compatible with Markdown.
"""

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pprint import pprint
from textwrap import dedent
from typing import Callable, Dict, Generator, Iterable, List, Optional, Tuple
import regex
from kmd.config.logger import get_logger
from kmd.config.text_styles import SYMBOL_PARA, SYMBOL_SENT
from kmd.model.errors_model import UnexpectedError
from kmd.text_handling.sentence_split_spacy import split_sentences
from kmd.text_handling.wordtoks import (
    is_break_or_space,
    is_tag,
    join_wordtoks,
    raw_text_to_wordtoks,
    SENT_BR_STR,
    SENT_BR_TOK,
    PARA_BR_STR,
    PARA_BR_TOK,
    wordtok_len,
)
from kmd.util.log_calls import tally_calls

log = get_logger(__name__)


def size_in_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def size_in_wordtoks(text: str) -> int:
    return len(raw_text_to_wordtoks(text))


class Unit(Enum):
    BYTES = "bytes"
    CHARS = "chars"
    WORDTOKS = "wordtoks"
    PARAGRAPHS = "paragraphs"
    SENTENCES = "sentences"


def size(text: str, unit: Unit) -> int:
    if unit == Unit.BYTES:
        return size_in_bytes(text)
    elif unit == Unit.CHARS:
        return len(text)
    elif unit == Unit.WORDTOKS:
        return size_in_wordtoks(text)
    else:
        raise UnexpectedError(f"Unsupported unit for string: {unit}")


@dataclass(frozen=True, order=True)
class SentIndex:
    """
    Point to a sentence in a TextDoc.
    """

    para_index: int
    sent_index: int

    def __str__(self):
        return f"{SYMBOL_PARA}{self.para_index},{SYMBOL_SENT}{self.sent_index}"


WordtokMapping = Dict[int, SentIndex]
"""A mapping from wordtok index to sentences in a TextDoc."""

SentenceMapping = Dict[SentIndex, List[int]]
"""A mapping from sentence index to wordtoks in a TextDoc."""


@dataclass
class Sentence:
    text: str
    char_offset: int  # Offset of the sentence in the original text.

    def size(self, unit: Unit) -> int:
        return size(self.text, unit)

    def as_wordtoks(self) -> List[str]:
        return raw_text_to_wordtoks(self.text)

    def __str__(self):
        return repr(self.text)


@dataclass
class Paragraph:
    original_text: str
    sentences: List[Sentence]
    char_offset: int  # Offset of the paragraph in the original text.

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(cls, text: str, char_offset: int = -1) -> "Paragraph":
        sent_values = split_sentences(text)
        sent_offset = 0
        sentences = []
        for sent_str in sent_values:
            sentences.append(Sentence(sent_str, sent_offset))
            sent_offset += len(sent_str) + len(SENT_BR_STR)
        return cls(original_text=text, sentences=sentences, char_offset=char_offset)

    def reassemble(self) -> str:
        return SENT_BR_STR.join(sent.text for sent in self.sentences)

    def replace_str(self, old: str, new: str):
        for sent in self.sentences:
            sent.text = sent.text.replace(old, new)

    def sent_iter(self, reverse: bool = False) -> Iterable[Tuple[int, Sentence]]:
        enum_sents = list(enumerate(self.sentences))
        return reversed(enum_sents) if reverse else enum_sents

    def size(self, unit: Unit) -> int:
        if unit == Unit.PARAGRAPHS:
            return 1
        if unit == Unit.SENTENCES:
            return len(self.sentences)

        base_size = sum(sent.size(unit) for sent in self.sentences)
        if unit == Unit.BYTES:
            return base_size + (len(self.sentences) - 1) * size_in_bytes(SENT_BR_STR)
        if unit == Unit.CHARS:
            return base_size + (len(self.sentences) - 1) * len(SENT_BR_STR)
        if unit == Unit.WORDTOKS:
            return base_size + (len(self.sentences) - 1)

        raise ValueError(f"Unsupported unit for Paragraph: {unit}")

    def as_wordtok_to_sent(self) -> Generator[Tuple[str, int], None, None]:
        last_sent_index = len(self.sentences) - 1
        for sent_index, sent in enumerate(self.sentences):
            for wordtok in sent.as_wordtoks():
                yield wordtok, sent_index
            if sent_index != last_sent_index:
                yield SENT_BR_TOK, sent_index

    def as_wordtoks(self) -> List[str]:
        return [wordtok for wordtok, _ in self.as_wordtok_to_sent()]


@dataclass
class TextDoc:
    paragraphs: List[Paragraph]

    # TODO: Could lazily compute paragraphs and wordtoks only for better performance.

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(cls, text: str) -> "TextDoc":
        text = text.strip()
        paragraphs = []
        char_offset = 0
        for para in text.split(PARA_BR_STR):
            stripped_para = para.strip()
            if stripped_para:
                paragraphs.append(Paragraph.from_text(stripped_para, char_offset))
                char_offset += len(para) + len(PARA_BR_STR)
        return cls(paragraphs=paragraphs)

    @classmethod
    def from_wordtoks(cls, wordtoks: List[str]) -> "TextDoc":
        return TextDoc.from_text(join_wordtoks(wordtoks))

    def reassemble(self) -> str:
        return PARA_BR_STR.join(paragraph.reassemble() for paragraph in self.paragraphs)

    def replace_str(self, old: str, new: str):
        for para in self.paragraphs:
            para.replace_str(old, new)

    def first_index(self) -> SentIndex:
        return SentIndex(0, 0)

    def last_index(self) -> SentIndex:
        return SentIndex(len(self.paragraphs) - 1, len(self.paragraphs[-1].sentences) - 1)

    def para_iter(self, reverse: bool = False) -> Iterable[Tuple[int, Paragraph]]:
        enum_paras = list(enumerate(self.paragraphs))
        return reversed(enum_paras) if reverse else enum_paras

    def sent_iter(self, reverse: bool = False) -> Iterable[Tuple[SentIndex, Sentence]]:
        for para_index, para in self.para_iter(reverse=reverse):
            for sent_index, sent in para.sent_iter(reverse=reverse):
                yield SentIndex(para_index, sent_index), sent

    def get_sent(self, index: SentIndex) -> Sentence:
        return self.paragraphs[index.para_index].sentences[index.sent_index]

    def set_sent(self, index: SentIndex, sent_str: str) -> None:
        old_sent = self.get_sent(index)
        self.paragraphs[index.para_index].sentences[index.sent_index] = Sentence(
            sent_str, old_sent.char_offset
        )

    def update_sent(self, index: SentIndex, transform: Callable[[str], str]) -> None:
        self.set_sent(index, transform(self.get_sent(index).text))

    def seek_to_sent(self, offset: int, unit: Unit) -> Tuple[SentIndex, int]:
        """
        Find the last sentence that starts before a given offset. Returns the SentIndex
        and the offset of the sentence start in the original document.
        """
        current_size = 0
        last_fit_index = None
        last_fit_offset = 0

        if unit == Unit.BYTES:
            size_sent_break = size_in_bytes(SENT_BR_STR)
            size_para_break = size_in_bytes(PARA_BR_STR)
        elif unit == Unit.CHARS:
            size_sent_break = len(SENT_BR_STR)
            size_para_break = len(PARA_BR_STR)
        elif unit == Unit.WORDTOKS:
            size_sent_break = 1
            size_para_break = 1
        else:
            raise UnexpectedError(f"Unsupported unit for seek_doc: {unit}")

        for para_index, para in enumerate(self.paragraphs):
            for sent_index, sent in enumerate(para.sentences):
                sentence_size = sent.size(unit)
                last_fit_index = SentIndex(para_index, sent_index)
                last_fit_offset = current_size
                if current_size + sentence_size + size_sent_break <= offset:
                    current_size += sentence_size
                    if sent_index < len(para.sentences) - 1:
                        current_size += size_sent_break
                else:
                    return last_fit_index, last_fit_offset
            if para_index < len(self.paragraphs) - 1:
                current_size += size_para_break

        if last_fit_index is None:
            raise ValueError("Cannot seek into empty document")

        return last_fit_index, last_fit_offset

    def sub_doc(self, first: SentIndex, last: Optional[SentIndex] = None) -> "TextDoc":
        """
        Get a sub-document. Inclusive ranges. Preserves original paragraph and sentence offsets.
        """
        if not last:
            last = self.last_index()
        if last > self.last_index():
            raise ValueError(f"End index out of range: {last} > {self.last_index()}")
        if first < self.first_index():
            raise ValueError(f"Start index out of range: {first} < {self.first_index()}")

        sub_paras = []
        for i in range(first.para_index, last.para_index + 1):
            para = self.paragraphs[i]
            if i == first.para_index and i == last.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[first.sent_index : last.sent_index + 1],
                        char_offset=para.char_offset,
                    )
                )
            elif i == first.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[first.sent_index :],
                        char_offset=para.char_offset,
                    )
                )
            elif i == last.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[: last.sent_index + 1],
                        char_offset=para.char_offset,
                    )
                )
            else:
                sub_paras.append(para)

        return TextDoc(sub_paras)

    def prev_sent(self, index: SentIndex) -> "SentIndex":
        if index.sent_index > 0:
            return SentIndex(index.para_index, index.sent_index - 1)
        elif index.para_index > 0:
            return SentIndex(
                index.para_index - 1, len(self.paragraphs[index.para_index - 1].sentences) - 1
            )
        else:
            raise ValueError("No previous sentence")

    def append_sent(self, sent: Sentence) -> None:
        if len(self.paragraphs) == 0:
            self.paragraphs.append(
                Paragraph(original_text=sent.text, sentences=[sent], char_offset=0)
            )
        else:
            last_para = self.paragraphs[-1]
            last_para.sentences.append(sent)

    def size(self, unit: Unit) -> int:
        if unit == Unit.PARAGRAPHS:
            return len(self.paragraphs)
        if unit == Unit.SENTENCES:
            return sum(len(para.sentences) for para in self.paragraphs)

        base_size = sum(para.size(unit) for para in self.paragraphs)
        if unit == Unit.BYTES:
            return base_size + (len(self.paragraphs) - 1) * size_in_bytes(PARA_BR_STR)
        if unit == Unit.CHARS:
            return base_size + (len(self.paragraphs) - 1) * len(PARA_BR_STR)
        if unit == Unit.WORDTOKS:
            return base_size + (len(self.paragraphs) - 1)

        raise ValueError(f"Unsupported unit for TextDoc: {unit}")

    def size_summary(self) -> str:
        return f"{self.size(Unit.BYTES)} bytes ({self.size(Unit.PARAGRAPHS)} paragraphs, {self.size(Unit.SENTENCES)} sentences)"

    def as_wordtok_to_sent(self) -> Generator[Tuple[str, SentIndex], None, None]:
        last_para_index = len(self.paragraphs) - 1
        for para_index, para in enumerate(self.paragraphs):
            for wordtok, sent_index in para.as_wordtok_to_sent():
                yield wordtok, SentIndex(para_index, sent_index)
            if para_index != last_para_index:
                yield PARA_BR_TOK, SentIndex(para_index, len(para.sentences) - 1)

    def as_wordtoks(self) -> List[str]:
        return [wordtok for wordtok, _sent_index in self.as_wordtok_to_sent()]

    def wordtok_mappings(self) -> Tuple[WordtokMapping, SentenceMapping]:
        """
        Get mappings between wordtok indexes and sentence indexes.
        """
        sent_indexes = [sent_index for _wordtok, sent_index in self.as_wordtok_to_sent()]

        wordtok_mapping = {i: sent_index for i, sent_index in enumerate(sent_indexes)}

        sent_mapping = defaultdict(list)
        for i, sent_index in enumerate(sent_indexes):
            sent_mapping[sent_index].append(i)

        return wordtok_mapping, sent_mapping

    def __str__(self):
        return f"TextDoc({self.size_summary()})"


## Tests


def test_document_parse_reassemble():
    text = dedent(
        """
        # Title

        Hello World. This is an example sentence. And here's another one!

        ## Subtitle

        This is a new paragraph.
        It has several sentences.
        There may be line breaks within a paragraph, but these should not affect handlingof the paragraph.
        There are also [links](http://www.google.com) and **bold** and *italic* text.

        ### Itemized List

        - Item 1

        - Item 2

        - Item 3

        ### Numbered List

        1. Item 1

        2. Item 2

        3. Item 3
        """
    ).strip()

    doc = TextDoc.from_text(text)

    print("\n---Original:")
    pprint(text)
    print("\n---Parsed:")
    pprint(doc)

    reassembled_text = doc.reassemble()

    # Should be exactly the same except for within-paragraph line breaks.
    def normalize(text):
        return regex.sub(r"\s+", " ", text.replace("\n\n", "<PARA>"))

    assert normalize(reassembled_text) == normalize(text)

    # Check offset of a paragraph towards the end of the document.
    last_para = doc.paragraphs[-1]
    last_para_char_offset = text.rindex(last_para.original_text)
    assert last_para.char_offset == last_para_char_offset


_simple_test_doc = dedent(
    """
    This is the first paragraph. It has multiple sentences.

    This is the second paragraph. It also has multiple sentences. And it continues.
    
    Here is the third paragraph. More sentences follow. And here is another one.
    """
).strip()


def test_seek_doc():
    doc = TextDoc.from_text(_simple_test_doc)

    offset = 1
    sent_index, sent_offset = doc.seek_to_sent(offset, Unit.BYTES)
    print(f"Seeked to {sent_index} offset {sent_offset} for offset {offset} bytes")
    assert sent_index == SentIndex(para_index=0, sent_index=0)
    assert sent_offset == 0

    offset = len("This is the first paragraph.")
    sent_index, sent_offset = doc.seek_to_sent(offset, Unit.BYTES)
    print(f"Seeked to {sent_index} offset {sent_offset} for offset {offset} bytes")
    assert sent_index == SentIndex(para_index=0, sent_index=0)
    assert sent_offset == 0

    offset = len("This is the first paragraph. ")
    sent_index, sent_offset = doc.seek_to_sent(offset, Unit.BYTES)
    print(f"Seeked to {sent_index} offset {sent_offset} for offset {offset} bytes")
    assert sent_index == SentIndex(para_index=0, sent_index=1)
    assert sent_offset == offset

    offset = len(
        "This is the first paragraph. It has multiple sentences.\n\nThis is the second paragraph."
    )
    sent_index, sent_offset = doc.seek_to_sent(offset, Unit.BYTES)
    print(f"Seeked to {sent_index} offset {sent_offset} for offset {offset} bytes")
    assert sent_index == SentIndex(para_index=1, sent_index=0)
    assert sent_offset == len("This is the first paragraph. It has multiple sentences.\n\n")

    offset = len(_simple_test_doc) + 10
    sent_index, sent_offset = doc.seek_to_sent(offset, Unit.BYTES)
    print(f"Seeked to {sent_index} offset {sent_offset} for offset {offset} bytes")
    assert sent_index == SentIndex(para_index=2, sent_index=2)


_short_test_doc = dedent(
    """
    Paragraph one.
    Sentence 1a. Sentence 1b. Sentence 1c.
    
    Paragraph two. Sentence 2a. Sentence 2b. Sentence 2c.
    
    Paragraph three. Sentence 3a. Sentence 3b. Sentence 3c.
    """
).strip()


def test_sub_doc():

    doc = TextDoc.from_text(_short_test_doc)

    sub_doc_start = SentIndex(1, 1)
    sub_doc_end = SentIndex(2, 1)
    sub_doc = doc.sub_doc(sub_doc_start, sub_doc_end)

    expected_text = dedent(
        """
        Sentence 2a. Sentence 2b. Sentence 2c.
        
        Paragraph three. Sentence 3a.
        """
    ).strip()
    expected_sub_doc = TextDoc.from_text(expected_text)

    print("---Original:")
    pprint(doc)
    print("---Subdoc:")
    pprint(sub_doc)

    # Confirm reassembled text is correct.
    assert sub_doc.reassemble() == expected_sub_doc.reassemble()

    # Confirm sentences and offsets are preserved in sub-doc.
    orig_sentences = [sent for _index, sent in doc.sent_iter()]
    sub_sentences = [sent for _index, sent in sub_doc.sent_iter()]
    assert orig_sentences[5:10] == sub_sentences

    # Confirm indexing and reverse iteration.
    assert doc.sub_doc(SentIndex(0, 0), None) == doc
    reversed_sentences = [sent for _index, sent in doc.sent_iter(reverse=True)]
    assert reversed_sentences == list(reversed(orig_sentences))


def test_tokenization():
    doc = TextDoc.from_text(_short_test_doc)
    wordtoks = doc.as_wordtoks()

    print("\n---Tokens:")
    pprint(wordtoks)

    assert wordtoks[:6] == ["Paragraph", " ", "one", ".", "<-SENT-BR->", "Sentence"]
    assert wordtoks[-7:] == [
        "3b",
        ".",
        "<-SENT-BR->",
        "Sentence",
        " ",
        "3c",
        ".",
    ]
    assert wordtoks.count(PARA_BR_TOK) == 2
    assert join_wordtoks(wordtoks) == _short_test_doc.replace(
        "\n", " ", 1
    )  # First \n is not a para break.


def test_wordtok_mappings():
    doc = TextDoc.from_text(_short_test_doc)

    print("\n---Mapping:")
    wordtok_mapping, sent_mapping = doc.wordtok_mappings()
    pprint(wordtok_mapping)
    pprint(sent_mapping)

    assert wordtok_mapping[0] == SentIndex(0, 0)
    assert wordtok_mapping[1] == SentIndex(0, 0)
    assert wordtok_mapping[4] == SentIndex(0, 0)
    assert wordtok_mapping[5] == SentIndex(0, 1)

    assert sent_mapping[SentIndex(0, 0)] == [0, 1, 2, 3, 4]
    assert sent_mapping[SentIndex(2, 3)] == [55, 56, 57, 58]


_sentence_tests = [
    "Hello, world!",
    "This is an example sentence with punctuation.",
    "And here's another one!",
    "Special characters: @#%^&*()",
]

_sentence_test_html = 'This is <span data-timestamp="1.234">a test</span>.'


def test_wordtokization():

    for sentence in _sentence_tests:
        wordtoks = raw_text_to_wordtoks(sentence)
        reassembled_sentence = "".join(wordtoks)
        assert reassembled_sentence == sentence

    assert raw_text_to_wordtoks("Multiple     spaces and tabs\tand\nnewlines in between.") == [
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
    assert raw_text_to_wordtoks("") == []
    assert raw_text_to_wordtoks("   ") == [" "]

    assert raw_text_to_wordtoks(_sentence_test_html) == [
        "This",
        " ",
        "is",
        " ",
        '<span data-timestamp="1.234">',
        "a",
        " ",
        "test",
        "</span>",
        ".",
    ]

    assert len(_sentence_test_html) == sum(
        wordtok_len(wordtok) for wordtok in raw_text_to_wordtoks(_sentence_test_html)
    )


def test_html_tokenization():
    doc = TextDoc.from_text(_sentence_test_html)

    print("\n---HTML Tokens:")
    pprint(doc.as_wordtoks())

    wordtoks = doc.as_wordtoks()
    assert wordtoks == [
        "This",
        " ",
        "is",
        " ",
        '<span data-timestamp="1.234">',
        "a",
        " ",
        "test",
        "</span>",
        ".",
    ]
    assert list(map(is_tag, wordtoks)) == [
        False,
        False,
        False,
        False,
        True,
        False,
        False,
        False,
        True,
        False,
    ]
    assert list(map(is_break_or_space, wordtoks)) == [
        False,
        True,
        False,
        True,
        False,
        False,
        True,
        False,
        False,
        False,
    ]
