import re
from kmd.model.html_conventions import CHUNK_DIV_BEGIN
from kmd.model.preconditions_model import precondition
from kmd.provenance.timestamps import TimestampExtractor
from kmd.media.media_services import get_media_id, youtube
from kmd.model.errors_model import PreconditionFailure
from kmd.model.items_model import Format, Item, ItemType


@precondition
def is_resource(item: Item) -> bool:
    return item.type == ItemType.resource


@precondition
def is_config(item: Item) -> bool:
    return item.type == ItemType.config


@precondition
def is_url(item: Item) -> bool:
    return item.url is not None


@precondition
def has_body(item: Item) -> bool:
    return bool(item.body)


@precondition
def has_text_body(item: Item) -> bool:
    return has_body(item) and item.format in (Format.plaintext, Format.markdown, Format.md_html)


@precondition
def is_plaintext(item: Item) -> bool:
    return has_body(item) and item.format == Format.plaintext


@precondition
def is_markdown(item: Item) -> bool:
    return has_body(item) and item.format in (Format.markdown, Format.md_html)


@precondition
def is_html(item: Item) -> bool:
    return has_body(item) and item.format == Format.html


@precondition
def has_div_chunks(item: Item) -> bool:
    return bool(item.body and item.body.find(CHUNK_DIV_BEGIN) != -1)


@precondition
def has_lots_of_html_tags(item: Item) -> bool:
    if not item.body:
        return False
    tag_free_body = re.sub(r"<[^>]*>", "", item.body)
    tag_chars = len(item.body) - len(tag_free_body)
    return tag_chars > max(5, len(item.body) * 0.1)


@precondition
def has_many_paragraphs(item: Item) -> bool:
    return bool(item.body and item.body.count("\n\n") > 4)


@precondition
def is_readable_text(item: Item) -> bool:
    return is_plaintext(item) or is_markdown(item)


@precondition
def is_timestamped_text(item: Item) -> bool:
    if not item.body:
        raise PreconditionFailure(f"Source item has no body: {item}")
    extractor = TimestampExtractor(item.body)
    extractor.precondition_check()
    return True


@precondition
def has_video_id(item: Item) -> bool:
    return bool(item.url and get_media_id(item.url))


@precondition
def is_youtube_video(item: Item) -> bool:
    return bool(item.url and youtube.canonicalize(item.url))