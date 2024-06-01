"""
Tools for handling documents consisting of sentences and paragraphs of text.
Compatible with Markdown.
"""

from dataclasses import dataclass
from enum import Enum
from pprint import pprint
from textwrap import dedent
from typing import Iterable, List, Optional, Tuple
from cachetools import cached
import regex
import spacy
from spacy.language import Language
from spacy.cli.download import download
from kmd.config.logger import get_logger
from kmd.text_handling.wordtoks import (
    join_wordtoks,
    sentence_as_wordtoks,
    SENT_BR_STR,
    SENT_BR_TOK,
    PARA_BR_STR,
    PARA_BR_TOK,
)

log = get_logger(__name__)


def spacy_download(model_name: str) -> Language:
    try:
        return spacy.load(model_name)
    except OSError:
        # If the model is not found, download it.
        log.message("Spacy model '%s' not found, so downloading it...", model_name)
        download(model_name)
        log.message("Downloaded Spacy model '%s'.", model_name)
        return spacy.load(model_name)


# Lazy load Spacy models.
class _Spacy:
    @cached(cache={})
    def load_model(self, model_name: str):
        return spacy_download(model_name)

    @property
    def en(self):
        return self.load_model("en_core_web_sm")


nlp = _Spacy()


def split_sentences(text: str) -> List[str]:
    """
    Split text into sentences. (English.)
    """
    return [sent.text.strip() for sent in nlp.en(text).sents]


def size_in_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def size_in_wordtoks(text: str) -> int:
    return len(sentence_as_wordtoks(text))


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
        raise ValueError(f"Unsupported unit for string: {unit}")


@dataclass(frozen=True, order=True)
class DocIndex:
    para_index: int
    sent_index: int

    def __str__(self):
        return f"¶{self.para_index},S{self.sent_index}"


@dataclass
class Sentence:
    text: str
    char_offset: int  # Offset of the sentence in the original text.

    def size(self, unit: Unit) -> int:
        return size(self.text, unit)

    def as_wordtoks(self) -> List[str]:
        return sentence_as_wordtoks(self.text)

    def __str__(self):
        return repr(self.text)


@dataclass
class Paragraph:
    original_text: str
    sentences: List[Sentence]
    char_offset: int  # Offset of the paragraph in the original text.

    @classmethod
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

    def as_wordtoks(self) -> Iterable[str]:
        last_sent_index = len(self.sentences) - 1
        for i, sent in enumerate(self.sentences):
            yield from sent.as_wordtoks()
            if i != last_sent_index:
                yield SENT_BR_TOK


@dataclass
class TextDoc:
    paragraphs: List[Paragraph]

    @classmethod
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

    def reassemble(self) -> str:
        return PARA_BR_STR.join(paragraph.reassemble() for paragraph in self.paragraphs)

    def first_index(self) -> DocIndex:
        return DocIndex(0, 0)

    def last_index(self) -> DocIndex:
        return DocIndex(len(self.paragraphs) - 1, len(self.paragraphs[-1].sentences) - 1)

    def sentence_iter(self, reverse: bool = False) -> Iterable[Tuple[DocIndex, Sentence]]:
        enum_paras = list(enumerate(self.paragraphs))
        for para_index, para in reversed(enum_paras) if reverse else enum_paras:
            enum_sents = list(enumerate(para.sentences))
            for sent_index, sent in reversed(enum_sents) if reverse else enum_sents:
                yield DocIndex(para_index, sent_index), sent

    def sub_doc(self, first: DocIndex, last: Optional[DocIndex] = None) -> "TextDoc":
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

    def prev_sent(self, index: DocIndex) -> "DocIndex":
        if index.sent_index > 0:
            return DocIndex(index.para_index, index.sent_index - 1)
        elif index.para_index > 0:
            return DocIndex(
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

    def as_wordtoks(self) -> Iterable[str]:
        last_para_index = len(self.paragraphs) - 1
        for i, para in enumerate(self.paragraphs):
            yield from para.as_wordtoks()
            if i != last_para_index:
                yield PARA_BR_TOK


## Tests


def test_document_parse_reassemble():
    # FIXME: Normalize Markdown so itemized lists are delimted by \n\n, or else they they are
    # broken incorrectly into sentences.
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


_short_text = dedent(
    """
    Paragraph one.
    Sentence 1a. Sentence 1b. Sentence 1c.
    
    Paragraph two. Sentence 2a. Sentence 2b. Sentence 2c.
    
    Paragraph three. Sentence 3a. Sentence 3b. Sentence 3c.
    """
).strip()


def test_sub_doc():

    doc = TextDoc.from_text(_short_text)

    sub_doc_start = DocIndex(1, 1)
    sub_doc_end = DocIndex(2, 1)
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
    orig_sentences = [sent for _index, sent in doc.sentence_iter()]
    sub_sentences = [sent for _index, sent in sub_doc.sentence_iter()]
    assert orig_sentences[5:10] == sub_sentences

    # Confirm indexing and reverse iteration.
    assert doc.sub_doc(DocIndex(0, 0), None) == doc
    reversed_sentences = [sent for _index, sent in doc.sentence_iter(reverse=True)]
    assert reversed_sentences == list(reversed(orig_sentences))


def test_tokenization():
    doc = TextDoc.from_text(_short_text)
    wordtoks = list(doc.as_wordtoks())

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
    assert join_wordtoks(wordtoks) == _short_text.replace(
        "\n", " ", 1
    )  # First \n is not a para break.
