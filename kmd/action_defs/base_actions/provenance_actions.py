from textwrap import indent
from kmd.action_exec.action_registry import kmd_action
from kmd.model.actions_model import (
    ONE_OR_MORE_ARGS,
    ChunkSize,
    EachItemAction,
)
from kmd.model.errors_model import InvalidInput, UnexpectedError
from kmd.model.items_model import Format, Item, ItemType
from kmd.config.logger import get_logger
from kmd.provenance.source_items import find_upstream_item, is_timestamped_text
from kmd.text_formatting.citations import add_citation_to_text, format_timestamp_citation
from kmd.provenance.extractors import TimestampExtractor
from kmd.text_docs.text_doc import TextDoc
from kmd.text_docs.token_mapping import TokenMapping
from kmd.text_docs.wordtoks import BOF_TOK, EOF_TOK, PARA_BR_TOK, SENT_BR_TOK, search_tokens

log = get_logger(__name__)


@kmd_action
class BackfillSourceTimestamps(EachItemAction):
    def __init__(self):
        super().__init__(
            name="backfill_source_timestamps",
            description="""
              Backfill timestamps from a source document.
              Seeks through the document this doc is derived from for timestamps and inserts them
              into the text of the current doc. Source must have similar tokens.
            """,
            expected_args=ONE_OR_MORE_ARGS,
            chunk_size=ChunkSize.PARAGRAPH,
        )

        if self.chunk_size == ChunkSize.SENTENCE:
            self.citation_tokens = [SENT_BR_TOK, PARA_BR_TOK, EOF_TOK]
        elif self.chunk_size == ChunkSize.PARAGRAPH:
            self.citation_tokens = [PARA_BR_TOK, EOF_TOK]
        else:
            raise UnexpectedError(f"Invalid text unit: {self.chunk_size}")

    def run_item(self, item: Item) -> Item:

        source_item = find_upstream_item(item, is_timestamped_text)

        source_url = source_item.url
        if not item.body:
            raise InvalidInput(f"Item must have a body: {item}")
        if not source_url:
            raise InvalidInput(f"Source item must have a URL: {source_item}")
        if not source_item.body:
            raise InvalidInput(f"Source item must have a body: {source_item}")

        log.message("Pulling timestamps from source item: %s", source_item.store_path)

        # Parse current doc.
        item_doc = TextDoc.from_text(item.body)
        item_wordtoks = item_doc.as_wordtoks(bof_eof=True)

        # Don't bother parsing sentences on the source document, which may be long and with HTML.
        extractor = TimestampExtractor(source_item.body)
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
        for wordtok_offset, (wordtok, sent_index) in enumerate(
            item_doc.as_wordtok_to_sent(bof_eof=True)
        ):
            if wordtok in self.citation_tokens:
                # If we're inserting citations at paragraph breaks, we need to back up to the beginning of the paragraph.
                # If we're inserting citations at sentence breaks, we can just use the per-sentence timestamps.
                if self.chunk_size == ChunkSize.PARAGRAPH:
                    start_para_index, start_para_wordtok = (
                        search_tokens(item_wordtoks)
                        .at(wordtok_offset)
                        .seek_back([BOF_TOK, PARA_BR_TOK])
                        .next()
                        .get_token()
                    )

                    log.info(
                        "Searching to previous para break behind %s (%s) got %s (%s)",
                        wordtok_offset,
                        wordtok,
                        start_para_index,
                        start_para_wordtok,
                    )

                    wordtok_offset = start_para_index

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
                            old_sent, format_timestamp_citation(source_url, timestamp)
                        ),
                    )

                else:
                    log.warning(
                        "Failed to extract timestamp at doc token offset %s: %s: %s",
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
