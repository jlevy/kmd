from os import path
from typing import Tuple, Optional
import re
from pathlib import Path
from kmd.model.errors_model import InvalidFilename
from kmd.model.items_model import FileExt, Format, Item, ItemType
from kmd.lang_tools.inflection import plural
from kmd.config.logger import get_logger

log = get_logger(__name__)


## File Naming Conventions

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


## File Utilities


def parse_filename(filename: str, expect_type_ext=False) -> Tuple[str, str, str, str]:
    """
    Parse a filename into its path, name, type, and extension parts.

    folder/file.name.type.ext -> ("folder", "file.name", "type", "ext")
    filename.note.txt -> ("", "filename", "note", "txt")
    filename.txt -> ("", "filename", "", "txt")
    filename -> ("", "filename", "", "")
    """
    dirname = path.dirname(filename)
    parts = path.basename(filename).rsplit(".", 2)
    if len(parts) == 3:
        name, item_type, ext = parts
    elif len(parts) == 2 and not expect_type_ext:
        name, ext = parts
        item_type = ""
    elif len(parts) == 1 and not expect_type_ext:
        name = parts[0]
        item_type = ext = ""
    else:
        raise InvalidFilename(
            f"Filename does not match file store convention (name.type.ext): {filename}"
        )
    return dirname, name, item_type, ext


def ext_is_text(file_ext: str) -> bool:
    return file_ext in ("txt", "md", "html", "htm", "json", "yaml", "yml")


def parse_check_filename(filename: str) -> Tuple[str, ItemType, FileExt]:
    # Python files can have only one dot (like file.py) but others should have a type
    # (like file.resource.yml).
    if filename.endswith(".py"):
        dirname, name, _, ext = parse_filename(filename, expect_type_ext=False)
        item_type = ItemType.extension.value
    else:
        dirname, name, item_type, ext = parse_filename(filename, expect_type_ext=True)
    try:
        return name, ItemType[item_type], FileExt[ext]
    except KeyError as e:
        raise InvalidFilename(f"Unknown type or extension for file: {filename}: {e}")


def format_from_ext(file_ext: FileExt) -> Optional[Format]:
    file_ext_to_format = {
        FileExt.html: Format.html,
        FileExt.md: Format.markdown,
        FileExt.txt: Format.plaintext,
        FileExt.pdf: Format.pdf,
        FileExt.yml: None,  # We will need to look at a YAML file to determine format.
        FileExt.py: Format.python,
    }
    return file_ext_to_format[file_ext]


_partial_file_pattern = re.compile(r".*\.partial\.[a-z0-9]+$")


def skippable_file(filename: str) -> bool:
    """
    Check if a file should be skipped when processing a directory.
    This skips .., .archive, .settings, __pycache__, .partial.xxx, etc.
    """

    return len(filename) > 1 and (
        filename.startswith(".")
        or filename.startswith("__")
        or bool(_partial_file_pattern.match(filename))
    )


## Tests


def test_parse_filename():
    import pytest

    filename = "foo/bar/test_file.1.type.ext"
    dirname, name, item_type, ext = parse_filename(filename)
    assert dirname == "foo/bar"
    assert name == "test_file.1"
    assert item_type == "type"
    assert ext == "ext"

    filename = "foo/bar/test_file.ext"
    dirname, name, item_type, ext = parse_filename(filename)
    assert dirname == "foo/bar"
    assert name == "test_file"
    assert item_type == ""
    assert ext == "ext"

    filename = "test_file"
    dirname, name, item_type, ext = parse_filename(filename)
    assert dirname == ""
    assert name == "test_file"
    assert item_type == ""
    assert ext == ""

    filename = "missing_type.ext"
    with pytest.raises(InvalidFilename):
        parse_filename(filename, expect_type_ext=True)
