from os import path
from typing import Tuple


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
        raise ValueError(
            f"Filename does not match file store convention (name.type.ext): {filename}"
        )
    return dirname, name, item_type, ext


#
# Tests


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
    with pytest.raises(ValueError):
        parse_filename(filename, expect_type_ext=True)
