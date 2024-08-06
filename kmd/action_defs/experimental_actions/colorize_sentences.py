from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    EachItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
from kmd.text_docs.text_doc import TextDoc, TextUnit
from kmd.text_formatting.html_in_md import html_span
from kmd.text_formatting.text_formatting import single_line


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
class ColorizeSentences(EachItemAction):
    def __init__(self):
        super().__init__(
            name="colorize_sentences",
            description="Color each sentence based on its length.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput("Item must have a body")

        doc = TextDoc.from_text(item.body)

        for para in doc.paragraphs:
            for sent in para.sentences:
                word_count = sent.size(TextUnit.WORDS)
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
            type=ItemType.note, body=doc.reassemble(), format=Format.md_html
        )

        return output_item
