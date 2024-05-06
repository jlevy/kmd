import enum

from kmd.model.model import Item, ItemType


class FileExt(enum.Enum):
    """File type extensions for items."""

    pdf = "pdf"
    txt = "txt"
    md = "md"
    webpage = "webpage"


def file_ext_for(item: Item) -> FileExt:
    item_type = item.type
    if item_type in [
        ItemType.note,
        ItemType.question,
        ItemType.concept,
        ItemType.answer,
    ]:
        return FileExt.md
    if item_type == ItemType.resource:
        if item.body:
            return FileExt.txt
        else:
            return FileExt.webpage
    raise ValueError(f"Unknown item type: {item_type}")
