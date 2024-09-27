from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.model import Format, Item, ItemType, PerItemAction
from kmd.preconditions.precondition_defs import has_text_body
from kmd.text_docs.wordtoks import insert_para_wordtoks, raw_text_to_wordtoks, visualize_wordtoks

log = get_logger(__name__)


@kmd_action
class Wordtokenize(PerItemAction):
    def __init__(self):
        super().__init__(
            name="wordtokenize",
            description="For debugging: Break text into word tokens.",
            precondition=has_text_body,
        )

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput(f"Item must have a body: {item}")

        new_title = f"Word tokens: {item.title}"
        toks_str = visualize_wordtoks(
            raw_text_to_wordtoks(insert_para_wordtoks(item.body), bof_eof=True)
        )
        output_item = item.derived_copy(
            type=ItemType.doc, title=new_title, body=toks_str, format=Format.markdown
        )

        return output_item
