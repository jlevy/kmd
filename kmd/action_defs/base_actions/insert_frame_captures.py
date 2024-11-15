from typing import List

from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.errors import ContentError, InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.media.image_similarity import filter_similar_frames
from kmd.media.video_frames import capture_frames
from kmd.model import (
    fmt_loc,
    Format,
    FRAME_CAPTURE,
    Item,
    ItemType,
    MediaType,
    Param,
    ParamList,
    PerItemAction,
    Precondition,
)
from kmd.preconditions.precondition_defs import has_frame_captures, has_timestamps, is_text_doc
from kmd.provenance.source_items import find_upstream_resource
from kmd.provenance.timestamps import TimestampExtractor
from kmd.text_chunks.parse_divs import parse_divs
from kmd.text_docs.search_tokens import search_tokens
from kmd.text_formatting.html_in_md import html_img, md_para
from kmd.util.string_replace import insert_multiple, Insertion
from kmd.util.url import as_file_url
from kmd.web_content.file_cache_tools import cache_file, cache_resource
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


@kmd_action
@dataclass
class InsertFrameCaptures(PerItemAction):

    name: str = "insert_frame_captures"

    description: str = """
        Look for timestamped video links and insert frame captures after each one.
        """

    precondition: Precondition = is_text_doc & has_timestamps & ~has_frame_captures

    params: ParamList = (
        Param(
            "threshold",
            "The similarity threshold for filtering consecutive frames.",
            default_value=0.6,
            type=float,
        ),
    )

    threshold: float = 0.6

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput("Item has no body")

        # Find the original video resource.
        orig_resource = find_upstream_resource(item)
        paths = cache_resource(orig_resource)
        if MediaType.video not in paths:
            raise InvalidInput(f"Item has no video: {item}")
        video_path = paths[MediaType.video]

        # Extract all timestamps.
        extractor = TimestampExtractor(item.body)
        timestamp_matches = list(extractor.extract_all())

        log.message(
            f"Found {len(timestamp_matches)} timestamps in the document, {parse_divs(item.body).size_summary()}."
        )

        # Extract frame captures.
        target_dir = current_workspace().base_dir / "assets"
        timestamps = [timestamp for timestamp, _index, _offset in timestamp_matches]
        frame_paths = capture_frames(video_path, timestamps, target_dir, prefix=item.title_slug())

        # Save images in file cache for later as well.
        for frame_path in frame_paths:
            cache_file(frame_path)
        log.message(f"Saved {len(frame_paths)} frame captures to cache.")

        # Filter out similar consecutive frames.
        unique_indices = filter_similar_frames(frame_paths, self.threshold)
        unique_frame_paths = [frame_paths[i] for i in unique_indices]
        unique_matches = [timestamp_matches[i] for i in unique_indices]

        log.message(
            f"Filtered out {len(frame_paths) - len(unique_frame_paths)}/{len(frame_paths)} similar frames."
        )
        log.message(
            f"Extracted {len(unique_frame_paths)} unique frame captures to: {fmt_loc(target_dir)}"
        )

        # Create a set of indices that were kept.
        kept_indices = set(unique_indices)

        # Prepare insertions.
        log.message(
            "Inserting %s frame captures, have %s wordtoks",
            len(unique_matches),
            len(extractor.offsets),
        )
        insertions: List[Insertion] = []
        for i, (timestamp, index, offset) in enumerate(timestamp_matches):
            # Only process timestamps whose frames weren't filtered out
            if i not in kept_indices:
                continue

            try:
                insert_index = (
                    search_tokens(extractor.wordtoks)
                    .at(index)
                    .seek_forward(["</span>"])
                    .next()
                    .get_index()
                )
            except KeyError:
                raise ContentError(
                    f"No matching tag close starting at {offset}: {extractor.wordtoks[offset:]}"
                )

            new_offset = extractor.offsets[insert_index]
            frame_path = frame_paths[i]
            insertions.append(
                (
                    new_offset,
                    md_para(
                        html_img(
                            as_file_url(frame_path),  # TODO: Serve these.
                            f"Frame at {timestamp} seconds",
                            class_name=FRAME_CAPTURE,
                        )
                    ),
                )
            )

        # Insert img tags into the document.
        output_text = insert_multiple(item.body, insertions)

        # Create output item.
        output_item = item.derived_copy(type=ItemType.doc, format=Format.md_html)
        output_item.body = output_text

        return output_item
