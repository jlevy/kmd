from pathlib import Path
from typing import Tuple

from kmd.config.logger import get_logger

from kmd.errors import InvalidFilename
from kmd.lang_tools.inflection import plural
from kmd.model.file_formats_model import FileExt, split_filename
from kmd.model.items_model import ItemType
from kmd.text_formatting.text_formatting import fmt_path

log = get_logger(__name__)


_type_to_folder = {name: plural(name) for name, _value in ItemType.__members__.items()}


def folder_for_type(item_type: ItemType) -> Path:
    """
    Relative Path for the folder containing this item type.

    doc -> docs
    resource -> resources
    config -> configs
    export -> exports
    etc.
    """
    return Path(_type_to_folder[item_type.name])


def join_suffix(base_slug: str, full_suffix: str) -> str:
    return f"{base_slug}.{full_suffix.lstrip('.')}"


def parse_filename_and_type(filename: str) -> Tuple[str, ItemType, FileExt]:
    """
    Parse a filename, confirm it's a recognized file extension. If the filename
    has a type in it, confirm it's a recognized type. Otherwise consider it a
    resource.
    """
    # Python files can have only one dot (like file.py) but others should have a type
    # (like file.resource.yml).
    if filename.endswith(".py"):
        dirname, name, _, ext = split_filename(filename, require_type_ext=False)
        item_type = ItemType.extension.value
    else:
        dirname, name, item_type, ext = split_filename(filename, require_type_ext=False)

    try:
        if not item_type:
            item_type = ItemType.resource.value
        return name, ItemType[item_type], FileExt[ext]
    except KeyError as e:
        raise InvalidFilename(f"Unknown type or extension for file: {fmt_path(filename)}: {e}")
