from pathlib import Path
from typing import Tuple
from kmd.model.errors_model import InvalidFilename
from kmd.model.file_formats_model import FileExt, parse_filename
from kmd.model.items_model import Item, ItemType
from kmd.lang_tools.inflection import plural
from kmd.config.logger import get_logger
from kmd.text_formatting.text_formatting import fmt_path

log = get_logger(__name__)


_type_to_folder = {name: plural(name) for name, _value in ItemType.__members__.items()}


def item_type_to_folder(item_type: ItemType) -> str:
    return _type_to_folder[item_type.name]


def item_type_folder_for(item: Item) -> Path:
    """
    Relative Path for the folder containing this item type.

    note -> notes, question -> questions, etc.
    """
    return Path(item_type_to_folder(item.type))


def join_filename(base_slug: str, full_suffix: str) -> str:
    return f"{base_slug}.{full_suffix}"


def parse_check_filename(filename: str) -> Tuple[str, ItemType, FileExt]:
    # Python files can have only one dot (like file.py) but others should have a type
    # (like file.resource.yml).
    if filename.endswith(".py"):
        dirname, name, _, ext = parse_filename(filename, expect_type_ext=False)
        item_type = ItemType.extension.value
    else:
        dirname, name, item_type, ext = parse_filename(filename, expect_type_ext=False)

    try:
        if not item_type:
            item_type = ItemType.doc.value
        return name, ItemType[item_type], FileExt[ext]
    except KeyError as e:
        raise InvalidFilename(f"Unknown type or extension for file: {fmt_path(filename)}: {e}")
