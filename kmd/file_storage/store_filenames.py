from pathlib import Path
from typing import Tuple

from kmd.config.logger import get_logger

from kmd.errors import InvalidFilename
from kmd.lang_tools.inflection import plural
from kmd.model.file_formats_model import FileExt, split_filename
from kmd.model.items_model import ItemType
from kmd.util.format_utils import fmt_path

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


def parse_filename_and_type(filename: str | Path) -> Tuple[str, ItemType, FileExt]:
    """
    Parse a filename according to naming conventions for the file store, i.e.
    `folder/name.type.ext`.
    Raises `InvalidFilename` if the filename does not have both a type and an extension.
    """
    # Python files can have only one dot (like file.py) but others should have a type
    # (like file.resource.yml).
    filename = str(filename)
    if filename.endswith(".py"):
        dirname, name, _, ext = split_filename(filename, require_type_ext=False)
        item_type = ItemType.extension.value
    else:
        dirname, name, item_type, ext = split_filename(filename, require_type_ext=False)

    if not item_type:
        raise InvalidFilename(
            f"Filename has no type (of the form `filename.type.ext`): {fmt_path(filename)}"
        )
    if not ext:
        raise InvalidFilename(f"Filename has no extension: {fmt_path(filename)}")
    try:
        return name, ItemType[item_type], FileExt[ext]
    except KeyError as e:
        raise InvalidFilename(
            f"Unknown type or extension for file: item_type={item_type}, ext={ext}, filename={fmt_path(filename)}"
        ) from e
