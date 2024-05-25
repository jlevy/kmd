"""
Tools for handling documents consisting of sentences and paragraphs of text.
Compatible with Markdown.
"""

from dataclasses import dataclass
from pprint import pprint
from textwrap import dedent
from typing import List
from cachetools import cached
import regex
import spacy
from spacy.language import Language
from spacy.cli.download import download
from kmd.config.logger import get_logger

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
    return [sent.text for sent in nlp.en(text).sents]


def size_in_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


# Use bytes throughout. May want to support token length or other metrics.
size = size_in_bytes

PARA_BREAK = "\n\n"
SPACE = " "

size_para_break = size(PARA_BREAK)
size_space = size(SPACE)


@dataclass(frozen=True)
class DocIndex:
    para_index: int
    sent_index: int


@dataclass
class Paragraph:
    original_text: str
    sentences: List[str]

    @classmethod
    def from_text(cls, text: str) -> "Paragraph":
        sentences = split_sentences(text)
        return cls(original_text=text, sentences=sentences)

    def size(self) -> int:
        return sum(size(sent) for sent in self.sentences) + (len(self.sentences) - 1) * size_space

    def reassemble(self) -> str:
        return SPACE.join(self.sentences)


@dataclass
class TextDoc:
    paragraphs: List[Paragraph]

    @classmethod
    def from_text(cls, text: str) -> "TextDoc":
        text = text.strip()
        paragraphs = [Paragraph.from_text(para) for para in text.split(PARA_BREAK) if para.strip()]
        return cls(paragraphs=paragraphs)

    def reassemble(self) -> str:
        return PARA_BREAK.join(paragraph.reassemble() for paragraph in self.paragraphs)

    def sub_doc(self, first: DocIndex, last: DocIndex) -> "TextDoc":
        """
        Get a sub-document. Inclusive ranges.
        """
        para_end = min(last.para_index, len(self.paragraphs) - 1)
        sub_paras = []
        for i in range(first.para_index, para_end + 1):
            para = self.paragraphs[i]
            if i == first.para_index and i == para_end:
                sub_paras.append(
                    Paragraph.from_text(
                        SPACE.join(para.sentences[first.sent_index : last.sent_index + 1])
                    )
                )
            elif i == first.para_index:
                sub_paras.append(
                    Paragraph.from_text(SPACE.join(para.sentences[first.sent_index :]))
                )
            elif i == para_end:
                sub_paras.append(
                    Paragraph.from_text(SPACE.join(para.sentences[: last.sent_index + 1]))
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

    def size(self) -> int:
        return (
            sum(para.size() for para in self.paragraphs)
            + (len(self.paragraphs) - 1) * size_para_break
        )


## Tests


def test_document_reassemble():
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

    def normalize(text):
        return regex.sub(r"\s+", " ", text.replace("\n\n", "<PARA>"))

    # Should be exactly the same except for within-paragraph line breaks.
    assert normalize(reassembled_text) == normalize(text)


def test_sub_doc():
    text = dedent(
        """
        Paragraph one. Sentence 1a. Sentence 1b. Sentence 1c.
        
        Paragraph two. Sentence 2a. Sentence 2b. Sentence 2c.
        
        Paragraph three. Sentence 3a. Sentence 3b. Sentence 3c.
        """
    ).strip()
    doc = TextDoc.from_text(text)

    sub_doc = doc.sub_doc(DocIndex(1, 1), DocIndex(2, 1))

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

    assert sub_doc.reassemble() == expected_sub_doc.reassemble()
