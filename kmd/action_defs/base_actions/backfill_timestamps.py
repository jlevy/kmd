from textwrap import indent
from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import (
    CachedDocAction,
)
from kmd.model.errors_model import ContentError, InvalidInput, UnexpectedError
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import is_timestamped_text, is_text_doc
from kmd.provenance.source_items import find_upstream_item
from kmd.text_docs.sizes import TextUnit
from kmd.text_formatting.citations import add_citation_to_text, format_timestamp_citation
from kmd.provenance.timestamps import TimestampExtractor
from kmd.text_docs.text_doc import TextDoc
from kmd.text_docs.token_mapping import TokenMapping
from kmd.text_docs.wordtoks import BOF_TOK, EOF_TOK, PARA_BR_TOK, SENT_BR_TOK, search_tokens
from kmd.text_formatting.text_formatting import fmt_path
from kmd.util.type_utils import not_none

log = get_logger(__name__)


@kmd_action()
class BackfillSourceTimestamps(CachedDocAction):
    def __init__(self):
        super().__init__(
            name="backfill_timestamps",
            description="""
              Backfill timestamps from a source document.
              Seeks through the document this doc is derived from for timestamps and inserts them
              into the text of the current doc. Source must have similar tokens.
            """,
            precondition=is_text_doc & ~is_timestamped_text,
            chunk_unit=TextUnit.paragraphs,
        )

        if self.chunk_unit not in (TextUnit.sentences, TextUnit.paragraphs):
            raise InvalidInput(
                f"Only support sentences and paragraphs for chunk unit: {self.chunk_unit}"
            )

        if self.chunk_unit == TextUnit.sentences:
            self.citation_tokens = [SENT_BR_TOK, PARA_BR_TOK, EOF_TOK]
        elif self.chunk_unit == TextUnit.paragraphs:
            self.citation_tokens = [PARA_BR_TOK, EOF_TOK]
        else:
            raise UnexpectedError(f"Invalid text unit: {self.chunk_unit}")

    def run_item(self, item: Item) -> Item:
        source_item = find_upstream_item(item, is_timestamped_text)

        source_url = source_item.url
        if not item.body:
            raise InvalidInput(f"Item must have a body: {item}")
        if not source_url:
            raise InvalidInput(f"Source item must have a URL: {source_item}")
        if not source_item.body:
            raise InvalidInput(f"Source item must have a body: {source_item}")

        log.message(
            "Pulling timestamps from source item: %s", fmt_path(not_none(source_item.store_path))
        )

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

        log.save_object("Token mapping", None, token_mapping.full_mapping_str())

        output_item = item.derived_copy(type=ItemType.doc, format=Format.md_html)

        timestamps_found = []
        for wordtok_offset, (wordtok, sent_index) in enumerate(
            item_doc.as_wordtok_to_sent(bof_eof=True)
        ):
            if wordtok in self.citation_tokens:
                # If we're inserting citations at paragraph breaks, we need to back up to the beginning of the paragraph.
                # If we're inserting citations at sentence breaks, we can just use the per-sentence timestamps.
                if self.chunk_unit == TextUnit.paragraphs:
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

                try:
                    timestamp = extractor.extract(source_wordtok_offset)
                    timestamps_found.append(timestamp)
                    item_doc.update_sent(
                        sent_index,
                        lambda old_sent: add_citation_to_text(
                            old_sent, format_timestamp_citation(source_url, timestamp)
                        ),
                    )
                except ContentError:
                    # Missing timestamps aren't fatal since it might be meta text like "Speaker 1:".
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
