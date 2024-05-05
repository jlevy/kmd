import enum

from kmd.model.model import Item, ItemTypeEnum


class FileExt(enum.Enum):
    """File type extensions for items."""

    pdf = "pdf"
    txt = "txt"
    md = "md"
    html = "html"
    url = "url"


def file_ext_for(item: Item) -> FileExt:
    item_type = item.type
    if item_type in [
        ItemTypeEnum.note,
        ItemTypeEnum.question,
        ItemTypeEnum.concept,
        ItemTypeEnum.answer,
    ]:
        return FileExt.md
    if item_type == ItemTypeEnum.resource:
        return FileExt.url
    raise ValueError(f"Unknown item type: {item_type}")
