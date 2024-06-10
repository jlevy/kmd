from textwrap import indent
from kmd.action_exec.action_registry import kmd_action
from kmd.config.text_styles import EMOJI_PROCESS
from kmd.file_storage.workspaces import current_workspace
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    EachItemAction,
)
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.model.locators import StorePath
from kmd.text_formatting.citations import add_citation_to_text, cite_video_timestamp
from kmd.extractors.extractors import TimestampExtractor
from kmd.text_docs.text_doc import TextDoc
from kmd.text_docs.token_mapping import TokenMapping
from kmd.text_docs.wordtoks import SENT_BR_TOK

log = get_logger(__name__)


def get_source_item(item: Item) -> Item:
    # TODO: Generalize this to traverse backwards until preconditions are met on a source item.

    if not item.relations.derived_from:
        raise InvalidInput(f"Item must be derived from another item: {item}")
    workspace = current_workspace()
    source_item = workspace.load(StorePath(item.relations.derived_from[0]))
    if not source_item.body:
        raise InvalidInput(f"Source item must have a body: {source_item}")
    return source_item


@kmd_action
class PullSourceTimestamps(EachItemAction):
    def __init__(self):
        super().__init__(
            name="pull_source_timestamps",
            friendly_name="Pull timestamps from a source document.",
            description="""
              Seeks through the document this doc is derived from for timestamps and inserts them
              into the text of the current doc. Source must have similar tokens.
            """,
            expected_args=ONE_OR_MORE_ARGS,
        )

        # TODO: Make settable:
        self.citation_tokens = [SENT_BR_TOK]
        self.extractor = TimestampExtractor

    def run_item(self, item: Item) -> Item:

        source_item = get_source_item(item)
        source_url = source_item.url
        if not item.body:
            raise InvalidInput(f"Item must have a body: {item}")
        if not source_url:
            raise InvalidInput(f"Source item must have a URL: {source_item}")
        if not source_item.body:
            raise InvalidInput(f"Source item must have a body: {source_item}")

        log.message(
            "%s Pulling timestamps from source item: %s", EMOJI_PROCESS, source_item.store_path
        )

        # Parse current doc.
        item_doc = TextDoc.from_text(item.body)
        item_wordtoks = item_doc.as_wordtoks()

        # Don't bother parsing sentences on the source document, which may be long and with HTML.
        extractor = self.extractor(source_item.body)
        extractor.precondition_check()
        source_wordtoks = extractor.wordtoks

        log.message(
            "Mapping source doc with %s wordtoks back to this item, %s.",
            len(source_wordtoks),
            item_doc.size_summary(),
        )

        token_mapping = TokenMapping(source_wordtoks, item_wordtoks)

        log.info(
            "Timestamp extractor mapping diff:\n%s",
            indent(token_mapping.diff.as_diff_str(include_equal=False), prefix="    "),
        )

        log.info("Token mapping:\n%s", indent(token_mapping.full_mapping_str(), prefix="    "))

        new_title = f"{item.title} (with timestamps)"
        output_item = item.derived_copy(type=ItemType.note, title=new_title, format=Format.markdown)

        timestamps_found = []
        for wordtok_offset, (wordtok, sent_index) in enumerate(item_doc.as_wordtok_to_sent()):
            if wordtok in self.citation_tokens:
                source_wordtok_offset = token_mapping.map_back(wordtok_offset)

                log.info(
                    "Mapping token at offset back to source doc: %s (%s) -> %s (%s)",
                    wordtok_offset,
                    wordtok,
                    source_wordtok_offset,
                    source_wordtoks[source_wordtok_offset],
                )

                timestamp = extractor.extract(source_wordtok_offset)

                if timestamp:
                    timestamps_found.append(timestamp)
                    item_doc.update_sent(
                        sent_index,
                        lambda old_sent: add_citation_to_text(
                            old_sent, cite_video_timestamp(source_url, timestamp)
                        ),
                    )

                else:
                    log.warning(
                        f"Failed to extract timestamp at doc token offset %s: %s: %s",
                        wordtok_offset,
                        sent_index,
                        wordtok,
                    )

        first = timestamps_found[0] if timestamps_found else "none"
        last = timestamps_found[-1] if timestamps_found else "none"
        log.message(
            "Found %s timestamps in source doc from %s to %s.", len(timestamps_found), first, last
        )
        output_item.body = item_doc.reassemble()

        # TODO: Insert time_stamp source metadata for source video (e.g. YouTube)

        return output_item
