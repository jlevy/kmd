from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import (
    ForEachItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import has_text_body
from kmd.text_docs.wordtoks import raw_text_to_wordtoks, visualize_wordtoks

log = get_logger(__name__)


@kmd_action()
class Wordtokenize(ForEachItemAction):
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
            raw_text_to_wordtoks(item.body, parse_para_br=True, bof_eof=True)
        )
        output_item = item.derived_copy(
            type=ItemType.note, title=new_title, body=toks_str, format=Format.markdown
        )

        return output_item
