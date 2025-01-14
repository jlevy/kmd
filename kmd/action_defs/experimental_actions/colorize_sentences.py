from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.model import Format, Item, ItemType, PerItemAction, Precondition
from kmd.preconditions.precondition_defs import is_text_doc
from kmd.text_docs.text_doc import TextDoc, TextUnit
from kmd.text_formatting.html_in_md import html_span
from kmd.util.format_utils import single_line


def color_by_length(count: int) -> str:
    if count < 7:
        color = "var(--blue-lighter)"
    elif count < 14:
        color = "var(--green-lighter)"
    elif count < 21:
        color = "var(--yellow-lighter)"
    elif count < 30:
        color = "var(--red-lighter)"
    else:
        color = "var(--magenta-lighter)"
    return color


@kmd_action
class ColorizeSentences(PerItemAction):

    name: str = "colorize_sentences"

    description: str = """
        Color each sentence based on its length.
        """

    precondition: Precondition = is_text_doc

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput("Item must have a body")

        doc = TextDoc.from_text(item.body)

        for para in doc.paragraphs:
            for sent in para.sentences:
                word_count = sent.size(TextUnit.words)
                color = color_by_length(word_count)
                sent.text = (
                    html_span(
                        single_line(sent.text),
                        class_name="highlight",
                        attrs={"style": f"background-color: {color}"},
                        safe=True,
                    )
                    + "\n"
                )

        output_item = item.derived_copy(
            type=ItemType.doc, body=doc.reassemble(), format=Format.md_html
        )

        return output_item
