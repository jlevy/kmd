from kmd.action_exec.action_registry import kmd_action
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    EachItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.text_docs.wordtoks import raw_text_to_wordtoks, visualize_wordtoks
from kmd.text_formatting.text_formatting import html_to_plaintext

log = get_logger(__name__)


@kmd_action
class StripHtml(EachItemAction):
    def __init__(self):
        super().__init__(
            name="strip_html",
            friendly_name="Strip HTML Tags",
            description="Strip HTML tags from text or Markdown.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput(f"Item must have a body: {item}")

        clean_body = html_to_plaintext(item.body)
        new_title = f"{item.title} (clean text)"
        output_item = item.derived_copy(
            type=ItemType.note, title=new_title, body=clean_body, format=Format.markdown
        )

        return output_item


@kmd_action
class Wordtokenize(EachItemAction):
    def __init__(self):
        super().__init__(
            name="wordtokenize",
            friendly_name="Word Tokenize",
            description="For debugging: Break text into word tokens.",
            expected_args=ONE_OR_MORE_ARGS,
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