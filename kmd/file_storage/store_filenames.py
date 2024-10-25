from pathlib import Path
from typing import Optional, Tuple

from kmd.config.logger import get_logger

from kmd.errors import InvalidFilename
from kmd.lang_tools.inflection import plural
from kmd.model.file_formats_model import FileExt, Format, split_filename
from kmd.model.items_model import ItemType

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


def parse_item_filename(
    path: str | Path,
) -> Tuple[str, Optional[ItemType], Optional[Format], FileExt]:
    """
    Parse a store file path into its name, format, and extension. Returns None for
    format or item type if not recognized. Raises `InvalidFilename` if the file extension
    is not recognized, since we expect all store files to have a recognized extension.
    """
    path_str = str(path)
    _dirname, name, item_type_str, ext_str = split_filename(path_str)
    file_ext = FileExt.parse(ext_str)
    if not file_ext:
        raise InvalidFilename(
            f"Unknown extension for file: {path_str} (recognized file extensions are {', '.join(FileExt.__members__.keys())})"
        )
    format = Format.guess_by_file_ext(file_ext)

    # TODO: For yaml file resources, look at the format in the metadata.

    item_type = None
    if item_type_str:
        try:
            item_type = ItemType(item_type_str)
        except ValueError:
            pass
    return name, item_type, format, file_ext
