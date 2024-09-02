from enum import Enum
from os import path
import re
from typing import Optional, Tuple
from kmd.model.errors_model import InvalidFilename


class Format(Enum):
    """
    Format of the data in this item. This is the body data format (or "url" for a URL resource).
    """

    url = "url"
    html = "html"
    markdown = "markdown"
    """`markdown` should be simple and clean Markdown that we can use with LLMs."""
    md_html = "md_html"
    """`md_html` is Markdown with HTML, used for example when we structure Markdown with divs."""
    plaintext = "plaintext"
    pdf = "pdf"
    yaml = "yaml"
    json = "json"
    python = "python"
    unknown = "unknown"

    def is_text(self) -> bool:
        return self not in [Format.pdf, Format.unknown]

    @classmethod
    def from_str(cls, ext_str: str) -> "Format":
        """
        Convert a string to a Format enum.
        Return None for unknown values.
        """
        ext = canonicalize_file_ext(ext_str)
        try:
            return Format(ext)
        except ValueError:
            return Format.unknown

    @classmethod
    def guess_by_file_ext(cls, file_ext: "FileExt") -> Optional["Format"]:
        """
        Guess the format for a given file extension. Doesn't work for .yml since that could be
        various formats. This doesn't need to be perfect, mainly used when importing files.
        """
        ext_to_format = {
            FileExt.html.value: Format.html,
            FileExt.md.value: Format.markdown,
            FileExt.txt.value: Format.plaintext,
            FileExt.pdf.value: Format.pdf,
            FileExt.py.value: Format.python,
        }
        return ext_to_format.get(file_ext.value, None)

    def __str__(self):
        return self.name


class FileExt(Enum):
    """
    Canonical file type extensions for items.
    """

    pdf = "pdf"
    txt = "txt"
    md = "md"
    yml = "yml"
    json = "json"
    html = "html"
    py = "py"

    def is_text(self) -> bool:
        return self in [self.txt, self.md, self.yml, self.html, self.json, self.py]

    @classmethod
    def for_format(cls, format: str | Format) -> Optional["FileExt"]:
        """
        Infer the file extension for a given format.
        """
        format_to_file_ext = {
            Format.html.value: FileExt.html,
            Format.url.value: FileExt.yml,
            Format.markdown.value: FileExt.md,
            Format.md_html.value: FileExt.md,
            Format.plaintext.value: FileExt.txt,
            Format.pdf.value: FileExt.pdf,
            Format.yaml.value: FileExt.yml,
            Format.python.value: FileExt.py,
        }

        return format_to_file_ext.get(str(format), None)

    def __str__(self):
        return self.name


def file_ext_is_text(ext: str) -> bool:
    """
    Check if a file extension is a text format.
    """
    ext = canonicalize_file_ext(ext)
    return Format.from_str(ext).is_text()


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


def parse_filename(filename: str, expect_type_ext=False) -> Tuple[str, str, str, str]:
    """
    Parse a filename into its path, name, (optional) type, and extension parts:

    folder/file.name.type.ext -> ("folder", "file.name", "type", "ext")
    filename.doc.txt -> ("", "filename", "note", "txt")
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


def skippable_filename(filename: str) -> bool:
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
