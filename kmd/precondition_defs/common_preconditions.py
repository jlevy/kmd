from kmd.model.html_conventions import CHUNK_DIV_BEGIN
from kmd.model.preconditions_model import precondition
from kmd.provenance.extractors import TimestampExtractor
from kmd.media.media_services import get_media_id, youtube
from kmd.model.errors_model import PreconditionFailure
from kmd.model.items_model import Format, Item, ItemType


@precondition
def is_resource(item: Item) -> bool:
    return item.type == ItemType.resource


@precondition
def is_url(item: Item) -> bool:
    return item.url is not None


@precondition
def has_body(item: Item) -> bool:
    return bool(item.body)


@precondition
def is_markdown(item: Item) -> bool:
    return has_body(item) and item.format in (Format.markdown, Format.md_html)


@precondition
def has_div_chunks(item: Item) -> bool:
    return bool(item.body and item.body.find(CHUNK_DIV_BEGIN) != -1)


@precondition
def has_video_id(item: Item) -> bool:
    return bool(item.url and get_media_id(item.url))


@precondition
def is_youtube_video(item: Item) -> bool:
    return bool(item.url and youtube.canonicalize(item.url))


@precondition
def is_timestamped_text(source_item: Item) -> bool:
    if not source_item.body:
        raise PreconditionFailure(f"Source item has no body: {source_item}")
    extractor = TimestampExtractor(source_item.body)
    extractor.precondition_check()
    return True
