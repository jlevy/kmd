import os
import re
from enum import Enum
from pathlib import Path
from typing import cast, List, Optional, Tuple

import magic

from kmd.errors import InvalidFilename
from kmd.text_formatting.text_formatting import fmt_path
from kmd.util.url import Url


class Format(Enum):
    """
    Format of data in a file or in an item. This is just the important formats, not an exhaustive
    list. For text items that have a body, this is the body data format. For resource items,
    it is the format of the resource (url, media, etc.).
    """

    url = "url"
    plaintext = "plaintext"
    markdown = "markdown"
    md_html = "md_html"
    """`md_html` is Markdown with HTML, used for example when we structure Markdown with divs."""
    html = "html"
    """`markdown` should be simple and clean Markdown that we can use with LLMs."""
    yaml = "yaml"
    python = "python"

    json = "json"
    csv = "csv"
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

    def supports_frontmatter(self) -> bool:
        return self in [
            self.url,
            self.plaintext,
            self.markdown,
            self.md_html,
            self.html,
            self.yaml,
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
            FileExt.txt.value: Format.plaintext,
            FileExt.md.value: Format.markdown,
            FileExt.html.value: Format.html,
            FileExt.yml.value: None,  # We will need to look at a YAML file to determine format.
            FileExt.json.value: Format.json,
            FileExt.csv.value: Format.csv,
            FileExt.py.value: Format.python,
            FileExt.pdf.value: Format.pdf,
            FileExt.docx.value: Format.docx,
            FileExt.mp3.value: Format.mp3,
            FileExt.m4a.value: Format.m4a,
            FileExt.mp4.value: Format.mp4,
        }
        return ext_to_format.get(file_ext.value, None)

    @classmethod
    def _init_mime_type_map(cls):
        Format._mime_type_map = {
            None: Format.url,  # URLs don't have a specific MIME type
            "text/plain": Format.plaintext,
            "text/markdown": Format.markdown,
            "text/x-markdown": Format.markdown,
            "text/html": Format.html,
            "application/yaml": Format.yaml,
            "application/x-yaml": Format.yaml,
            "text/x-python": Format.python,
            "application/json": Format.json,
            "text/csv": Format.csv,
            "application/pdf": Format.pdf,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": Format.docx,
            "audio/mpeg": Format.mp3,
            "audio/mp3": Format.mp3,
            "audio/mp4": Format.m4a,
            "video/mp4": Format.mp4,
        }

    def mime_type(self) -> Optional[str]:
        """
        MIME type for the format, or None if not recognized.
        """
        for mime_type, format in self._mime_type_map.items():
            if format == self:
                return mime_type
        return None

    @classmethod
    def from_mime_type(cls, mime_type: Optional[str]) -> Optional["Format"]:
        """
        Format from mime type, or Format.unknown if not recognized.
        """
        return cls._mime_type_map.get(mime_type, Format.unknown)

    def __str__(self):
        return self.name


Format._init_mime_type_map()


class FileExt(Enum):
    """
    Canonical file type extensions for items.
    """

    txt = "txt"
    md = "md"
    html = "html"
    yml = "yml"
    json = "json"
    csv = "csv"
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
            Format.json.value: FileExt.json,
            Format.csv.value: FileExt.csv,
            Format.python.value: FileExt.py,
            Format.pdf.value: FileExt.pdf,
            Format.docx.value: FileExt.docx,
            Format.mp3.value: FileExt.mp3,
            Format.m4a.value: FileExt.m4a,
            Format.mp4.value: FileExt.mp4,
        }

        return format_to_file_ext.get(str(format), None)

    @classmethod
    def parse(cls, ext_str: str) -> Optional["FileExt"]:
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


def canonicalize_file_ext(ext: str) -> str:
    """
    Convert a file extension (with or without the dot) to canonical form (without the dot).
    """
    ext_map = {
        "htm": "html",
        "yaml": "yml",
    }
    ext = ext.lower().lstrip(".")
    return ext_map.get(ext, ext)


def parse_file_ext(path: str | Path) -> Optional[FileExt]:
    """
    Parse a file extension from a path or a raw file extension like "csv" or ".csv".
    """
    front, ext = os.path.splitext(str(path))
    if not ext:
        ext = front
    return FileExt.parse(canonicalize_file_ext(ext))


def guess_format(path: str | Path) -> Optional[Format]:
    """
    Guess the format of a file from its extension. None if not clear.
    """
    _dirname, _name, _item_type, ext = split_filename(path)
    file_ext = parse_file_ext(ext)
    format = file_ext and Format.guess_by_file_ext(file_ext)
    return format


def split_filename(path: str | Path, require_type_ext: bool = False) -> Tuple[str, str, str, str]:
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
    elif len(parts) == 2 and not require_type_ext:
        name, ext = parts
        item_type = ""
    elif len(parts) == 1 and not require_type_ext:
        name = parts[0]
        item_type = ext = ""
    else:
        raise InvalidFilename(
            f"Filename does not match file store convention (name.type.ext): {path_str}"
        )
    return dirname, name, item_type, ext


def join_filename(dirname: str | Path, name: str, item_type: Optional[str], ext: str) -> Path:
    """
    Join a filename into a single path, with optional type and extension.
    """

    parts = cast(List[str], filter(bool, [name, item_type, ext]))
    return Path(dirname) / ".".join(parts)


def parse_file_format(path: str | Path) -> Tuple[str, Format, FileExt]:
    """
    Parse a file path into its name, format, and extension, raising exceptions if they
    are not recognized.
    """
    path_str = str(path)
    try:
        _dirname, name, _item_type, ext_str = split_filename(path_str)
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


def file_mime_type(filename: str | Path) -> str:
    """
    Get the mime type of a file using libmagic.
    """
    filename = str(filename)
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(filename)
    return mime_type or "unknown"


def file_format(filename: str | Path) -> Optional[Format]:
    """
    Get file format based on libmagic mime type.
    """
    return Format.from_mime_type(file_mime_type(filename))


def file_ext_from_name(url_or_path: Url | Path) -> Optional[FileExt]:
    """
    Recognize known file extensions from the path or URL.
    """

    return parse_file_ext(url_or_path)


def file_ext_from_content(path: Path) -> Optional[FileExt]:
    """
    Recognize known file extensions from the content.
    """
    fmt = file_format(path)
    return FileExt.for_format(fmt) if fmt else None


## Tests


def test_parse_filename():
    import pytest

    filename = "foo/bar/test_file.1.type.ext"
    dirname, name, item_type, ext = split_filename(filename)
    assert dirname == "foo/bar"
    assert name == "test_file.1"
    assert item_type == "type"
    assert ext == "ext"

    filename = "foo/bar/test_file.ext"
    dirname, name, item_type, ext = split_filename(filename)
    assert dirname == "foo/bar"
    assert name == "test_file"
    assert item_type == ""
    assert ext == "ext"

    filename = "test_file"
    dirname, name, item_type, ext = split_filename(filename)
    assert dirname == ""
    assert name == "test_file"
    assert item_type == ""
    assert ext == ""

    filename = "missing_type.ext"
    with pytest.raises(InvalidFilename):
        split_filename(filename, require_type_ext=True)


def test_parse_file_ext():
    assert parse_file_ext("test.md") == FileExt.md
    assert parse_file_ext("test.resource.md") == FileExt.md
    assert parse_file_ext(".md") == FileExt.md
    assert parse_file_ext("md") == FileExt.md
    assert parse_file_ext("foobar") is None
    assert parse_file_ext(Url("http://example.com/test.md")) == FileExt.md
    assert parse_file_ext(Url("http://example.com/test")) is None
