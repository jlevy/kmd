import re

from kmd.media.media_services import get_media_id, youtube
from kmd.model.doc_elements import ANNOTATED_PARA, CHUNK
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType
from kmd.model.preconditions_model import precondition
from kmd.provenance.timestamps import TIMESTAMP_RE
from kmd.text_docs.wordtoks import first_wordtok_is_div
from kmd.text_formatting.markdown_util import extract_bullet_points


@precondition
def is_resource(item: Item) -> bool:
    return item.type == ItemType.resource


@precondition
def is_concept(item: Item) -> bool:
    return item.type == ItemType.concept


@precondition
def is_config(item: Item) -> bool:
    return item.type == ItemType.config


@precondition
def is_instruction(item: Item) -> bool:
    return item.type == ItemType.instruction


@precondition
def is_url(item: Item) -> bool:
    return item.type == ItemType.resource and item.url is not None


@precondition
def is_audio_resource(item: Item) -> bool:
    return bool(item.type == ItemType.resource and item.format and item.format.is_audio())


@precondition
def is_video_resource(item: Item) -> bool:
    return bool(item.type == ItemType.resource and item.format and item.format.is_video())


@precondition
def has_body(item: Item) -> bool:
    return bool(item.body and item.body.strip())


@precondition
def has_text_body(item: Item) -> bool:
    return has_body(item) and item.format in (Format.plaintext, Format.markdown, Format.md_html)


@precondition
def has_html_body(item: Item) -> bool:
    return has_body(item) and item.format in (Format.html, Format.md_html)


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
def is_text_doc(item: Item) -> bool:
    """
    A document that can be processed by LLMs and other plaintext tools.
    """
    return (is_plaintext(item) or is_markdown(item)) and has_body(item)


@precondition
def is_markdown_list(item: Item) -> bool:
    try:
        return (
            is_markdown(item)
            and item.body is not None
            and len(extract_bullet_points(item.body)) >= 2
        )
    except TypeError:
        return False


@precondition
def has_div_chunks(item: Item) -> bool:
    return bool(item.body and item.body.find(f'<div class="{CHUNK}">') != -1)


@precondition
def has_annotated_paras(item: Item) -> bool:
    return bool(item.body and item.body.find(f'<p class="{ANNOTATED_PARA}">') != -1)


@precondition
def starts_with_div(item: Item) -> bool:
    return bool(item.body and first_wordtok_is_div(item.body))


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
def has_timestamps(item: Item) -> bool:
    return bool(item.body and TIMESTAMP_RE.search(item.body))


@precondition
def has_video_id(item: Item) -> bool:
    return bool(item.url and get_media_id(item.url))


@precondition
def is_youtube_video(item: Item) -> bool:
    return bool(item.url and youtube.canonicalize(item.url))
