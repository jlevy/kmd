import os
import re
from enum import Enum
from pathlib import Path
from typing import cast, List, Optional, Tuple

import magic

from kmd.errors import InvalidFilename
from kmd.model.media_model import MediaType
from kmd.util.url import is_file_url, parse_file_url, Url


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
    jpeg = "jpeg"
    png = "png"
    mp3 = "mp3"
    m4a = "m4a"
    mp4 = "mp4"

    binary = "binary"

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

    def media_format(self) -> MediaType:
        format_to_media_format = {
            Format.url: MediaType.webpage,
            Format.plaintext: MediaType.text,
            Format.markdown: MediaType.text,
            Format.md_html: MediaType.text,
            Format.html: MediaType.webpage,
            Format.yaml: MediaType.text,
            Format.python: MediaType.text,
            Format.json: MediaType.text,
            Format.csv: MediaType.text,
            Format.pdf: MediaType.text,
            Format.jpeg: MediaType.image,
            Format.png: MediaType.image,
            Format.docx: MediaType.text,
            Format.mp3: MediaType.audio,
            Format.m4a: MediaType.audio,
            Format.mp4: MediaType.video,
        }
        return format_to_media_format.get(self, MediaType.binary)

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
            FileExt.jpg.value: Format.jpeg,
            FileExt.png.value: Format.png,
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
            "image/jpeg": Format.jpeg,
            "image/png": Format.png,
            "audio/mpeg": Format.mp3,
            "audio/mp3": Format.mp3,
            "audio/mp4": Format.m4a,
            "video/mp4": Format.mp4,
            "application/octet-stream": Format.binary,
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
        Format from mime type.
        """
        return cls._mime_type_map.get(mime_type)

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
    jpg = "jpg"
    png = "png"
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
            Format.url.value: FileExt.yml,  # We save URLs as YAML resources.
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
            Format.jpeg.value: FileExt.jpg,
            Format.png.value: FileExt.png,
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
        "jpeg": "jpg",
    }
    ext = ext.lower().lstrip(".")
    return ext_map.get(ext, ext)


def parse_file_ext(url_or_path: str | Url | Path) -> Optional[FileExt]:
    """
    Parse a known, canonical file extension from a path, a URL, or even just a
    raw file extension (like "csv" or ".csv").
    """
    front, ext = os.path.splitext(str(url_or_path).split("/")[-1])
    if not ext:
        ext = front
    return FileExt.parse(canonicalize_file_ext(ext))


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


_hidden_file_pattern = re.compile(r"\.[^.]+")
_partial_file_pattern = re.compile(r".*\.partial(\.[a-z0-9]+)?$")


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


def is_full_html_page(content: str) -> bool:
    """
    A full HTML document that is probably best rendered in a browser.
    """
    return bool(re.search(r"<!DOCTYPE html>|<html>|<body>|<head>", content, re.IGNORECASE))


def is_html(content: str) -> bool:
    """
    Check if the content is HTML.
    """
    return bool(
        re.search(
            r"<!DOCTYPE html>|<html>|<body>|<head>|<div>|<p>|<img |<a href", content, re.IGNORECASE
        )
    )


def is_markdown(content: str) -> bool:
    """
    Check if the content is Markdown.
    """
    return bool(re.search(r"^#+ |^- |\*\*|__", content, re.MULTILINE))


def read_partial_text(
    path: Path, max_bytes: int = 200 * 1024, encoding: str = "utf-8", errors: str = "strict"
) -> Optional[str]:
    try:
        with path.open("r", encoding=encoding, errors=errors) as file:
            return file.read(max_bytes)
    except UnicodeDecodeError:
        return None


def detect_mime_type(filename: str | Path) -> Optional[str]:
    """
    Get the mime type of a file using heuristics for HTML and Markdown and libmagic.
    """
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(str(filename))
    path = Path(filename)
    if (not mime_type or mime_type == "text/plain") and path.is_file():
        # Also try detecting HTML and Markdown directly to discriminate these from plaintext.
        content = read_partial_text(path)
        if content and is_html(content):
            mime_type = "text/html"
        elif content and is_markdown(content):
            mime_type = "text/markdown"

    return mime_type


def detect_file_format(path: str | Path) -> Optional[Format]:
    """
    Get file format based on file extension and file content (libmagic and heuristics).
    """
    path = Path(path)

    # First, try by filename.
    ext = parse_file_ext(path)
    fmt = None
    if ext:
        fmt = Format.guess_by_file_ext(ext)

    # Next, try by mime type.
    if not fmt:
        fmt = Format.from_mime_type(detect_mime_type(path))

    return fmt


def detect_media_type(filename: str | Path) -> MediaType:
    """
    Get media type (text, image, video etc.) based on file content (libmagic).
    """
    fmt = detect_file_format(filename)
    media_format = fmt.media_format() if fmt else MediaType.binary
    return media_format


def file_ext_from_content(path: Path) -> Optional[FileExt]:
    """
    Recognize known file extensions from the content.
    """
    fmt = detect_file_format(path)
    return FileExt.for_format(fmt) if fmt else None


def choose_file_ext(url_or_path: Url | Path) -> Optional[FileExt]:
    """
    Pick a suffix to reflect the type of the content. Recognizes known file
    extensions, then tries libmagic, then gives up (returns None).
    """

    if isinstance(url_or_path, Path):
        ext = parse_file_ext(url_or_path) or file_ext_from_content(url_or_path)
    elif is_file_url(url_or_path):
        path = parse_file_url(url_or_path)
        if path:
            ext = parse_file_ext(path) or file_ext_from_content(path)
    else:
        ext = parse_file_ext(url_or_path)

    return ext


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
