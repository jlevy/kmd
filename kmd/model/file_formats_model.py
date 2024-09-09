from enum import Enum
import os
from pathlib import Path
import re
from typing import Optional, Tuple
from kmd.model.errors_model import InvalidFilename
from kmd.text_formatting.text_formatting import fmt_path


class Format(Enum):
    """
    Format of the data in this item. This is the body data format (or "url" for a URL resource).
    """

    url = "url"
    plaintext = "plaintext"
    markdown = "markdown"
    md_html = "md_html"
    """`md_html` is Markdown with HTML, used for example when we structure Markdown with divs."""
    html = "html"
    """`markdown` should be simple and clean Markdown that we can use with LLMs."""
    yaml = "yaml"
    json = "json"
    python = "python"
    pdf = "pdf"
    docx = "docx"
    mp3 = "mp3"
    m4a = "m4a"
    mp4 = "mp4"
    unknown = "unknown"

    def is_text(self) -> bool:
        """
        Can this format be read into a string and processed by text tools?
        """
        return self in [
            self.plaintext,
            self.markdown,
            self.md_html,
            self.html,
            self.yaml,
            self.json,
            self.python,
        ]

    def is_audio(self) -> bool:
        return self in [self.mp3, self.m4a]

    def is_video(self) -> bool:
        return self in [self.mp4]

    @classmethod
    def guess_by_file_ext(cls, file_ext: "FileExt") -> Optional["Format"]:
        """
        Guess the format for a given file extension, if it determines the format,
        None if format is ambiguous.
        """
        ext_to_format = {
            FileExt.yml: None,  # We will need to look at a YAML file to determine format.
            FileExt.txt.value: Format.plaintext,
            FileExt.md.value: Format.markdown,
            FileExt.json.value: Format.json,
            FileExt.html.value: Format.html,
            FileExt.pdf.value: Format.pdf,
            FileExt.docx.value: Format.docx,
            FileExt.py.value: Format.python,
            FileExt.mp3.value: Format.mp3,
            FileExt.m4a.value: Format.m4a,
            FileExt.mp4.value: Format.mp4,
        }
        return ext_to_format.get(file_ext.value, None)

    def __str__(self):
        return self.name


class FileExt(Enum):
    """
    Canonical file type extensions for items.
    """

    txt = "txt"
    md = "md"
    html = "html"
    yml = "yml"
    json = "json"
    py = "py"
    pdf = "pdf"
    docx = "docx"
    mp3 = "mp3"
    m4a = "m4a"
    mp4 = "mp4"

    def is_text(self) -> bool:
        return self in [
            self.txt,
            self.md,
            self.html,
            self.yml,
            self.json,
            self.py,
        ]

    @classmethod
    def for_format(cls, format: str | Format) -> Optional["FileExt"]:
        """
        File extension to use for a given format.
        """
        format_to_file_ext = {
            Format.url.value: FileExt.yml,
            Format.markdown.value: FileExt.md,
            Format.md_html.value: FileExt.md,
            Format.html.value: FileExt.html,
            Format.plaintext.value: FileExt.txt,
            Format.yaml.value: FileExt.yml,
            Format.python.value: FileExt.py,
            Format.pdf.value: FileExt.pdf,
            Format.docx.value: FileExt.docx,
            Format.mp3.value: FileExt.mp3,
            Format.m4a.value: FileExt.m4a,
            Format.mp4.value: FileExt.mp4,
        }

        return format_to_file_ext.get(str(format), None)

    @classmethod
    def from_str(cls, ext_str: str) -> Optional["FileExt"]:
        """
        Convert a string to a FileExt enum.
        """
        ext = canonicalize_file_ext(ext_str)
        try:
            return FileExt(ext)
        except ValueError:
            return None

    def __str__(self):
        return self.name


def file_ext_is_text(ext: str) -> bool:
    """
    Check if a file extension is a text format.
    """
    file_ext = FileExt.from_str(canonicalize_file_ext(ext))
    return bool(file_ext and file_ext.is_text())


def canonicalize_file_ext(ext: str) -> str:
    """
    Convert a file extension to canonical form (without the dot).
    """
    ext_map = {
        "htm": "html",
        "yaml": "yml",
    }
    ext = ext.lower().lstrip(".")
    return ext_map.get(ext, ext) or ext


def parse_filename(path: str | Path, expect_type_ext=False) -> Tuple[str, str, str, str]:
    """
    Parse a filename into its path, name, (optional) type, and extension parts:

    folder/file.name.type.ext -> ("folder", "file.name", "type", "ext")
    filename.doc.txt -> ("", "filename", "note", "txt")
    filename.txt -> ("", "filename", "", "txt")
    filename -> ("", "filename", "", "")
    """
    path_str = str(path)

    dirname = os.path.dirname(path_str)
    parts = os.path.basename(path_str).rsplit(".", 2)
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
            f"Filename does not match file store convention (name.type.ext): {path_str}"
        )
    return dirname, name, item_type, ext


def parse_file_format(path: str | Path) -> Tuple[str, Format, FileExt]:
    """
    Parse a file path into its name, format, and extension, raising exceptions if they
    are not recognized.
    """
    path_str = str(path)
    try:
        _dirname, name, _item_type, ext_str = parse_filename(path_str)
        file_ext = FileExt(ext_str)
    except ValueError:
        raise InvalidFilename(
            f"Unknown extension for file: {path_str} (recognized file extensions are {', '.join(FileExt.__members__.keys())})"
        )
    format = Format.guess_by_file_ext(file_ext)
    if not format:
        raise InvalidFilename(
            f"Unknown format for file (check the file ext?): {fmt_path(path_str)}"
        )

    # TODO: For yaml file resources, look at the format in the metadata.

    return name, format, file_ext


_hidden_file_pattern = re.compile(r"\.[^.]+")
_partial_file_pattern = re.compile(r".*\.partial\.[a-z0-9]+$")


def is_ignored(path: str | Path) -> bool:
    """
    Whether a file or path should be skipped when processing a directory.
    This skips .., .archive, .settings, __pycache__, .partial.xxx, etc.
    """
    name = os.path.basename(path)
    return (
        bool(_hidden_file_pattern.match(name))
        or name.startswith("__")
        or bool(_partial_file_pattern.match(name))
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
