"""
Frontmatter format: Read and write files with YAML frontmatter, to support convenient
metadata on text files in a way that is compatible with browsers, editors, and Markdown
parsers.

This is a generalization of the common format used by Jekyll and other CMSs for
Markdown files.

Frontmatter may be enclosed in `---` delimiters, as is typical with many
Markdown files. But in this generalized format, it can also be enclosed in
`<!---` and `--->` delimiters for convenience in text or HTML files, or between
`#---` and `#---` delimiters for Python and other code files. These markers must
be alone on their own lines.

This is a simple implementation that supports reading small files very easily
but also allows extracting frontmatter without reading an entire file, with or
without YAML parsing.
"""

import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Any, cast, Dict, Optional, Tuple

from ruamel.yaml.error import YAMLError
from strif import atomic_output_file

from kmd.errors import FileFormatError, FileNotFound
from kmd.file_formats.yaml_util import (
    custom_key_sort,
    from_yaml_string,
    KeySort,
    to_yaml_string,
    write_yaml,
)
from kmd.util.format_utils import fmt_path


class FmFormat(Enum):
    yaml = ("---", "---", "")
    html = ("<!---", "--->", "")
    code = ("#---", "#---", "# ")

    @property
    def start(self):
        return self.value[0]

    @property
    def end(self):
        return self.value[1]

    @property
    def prefix(self):
        return self.value[2]


def fmf_write(
    file_path: Path | str,
    content: str,
    metadata: Optional[Dict],
    format: FmFormat = FmFormat.yaml,
    key_sort: Optional[KeySort] = None,
) -> None:
    """
    Write the given Markdown text content to a file, with associated YAML metadata, in a
    generalized Jekyll-style frontmatter format.
    """
    with atomic_output_file(file_path, make_parents=True) as temp_output:
        with open(temp_output, "w") as f:
            if metadata:
                f.write(format.start)
                f.write("\n")
                for line in to_yaml_string(metadata, key_sort=key_sort).splitlines():
                    f.write(format.prefix + line)
                    f.write("\n")
                f.write(format.end)
                f.write("\n")

            f.write(content)


Metadata = Dict[str, Any]


def fmf_read(file_path: Path | str) -> Tuple[str, Optional[Metadata]]:
    """
    Read UTF-8 text content (typically Markdown) from a file with optional YAML metadata
    in Jekyll-style frontmatter format. Auto-detects variant formats for HTML and code
    (Python style) based on whether the prefix is `---` or `<!---` or `#---`.
    Reads the entire file into memory.
    """
    content, metadata_str = fmf_read_raw(file_path)
    metadata = None
    if metadata_str:
        try:
            metadata = from_yaml_string(metadata_str)
        except YAMLError as e:
            raise FileFormatError(f"Error parsing YAML metadata: {fmt_path(file_path)}: {e}")
        if not isinstance(metadata, dict):
            raise FileFormatError(f"Invalid metadata type: {type(metadata)}")
        metadata = cast(Metadata, metadata)
    return content, metadata


def fmf_read_frontmatter(file_path: Path | str) -> Tuple[Optional[str], int]:
    """
    Reads the metadata frontmatter from the file and returns the metadata string and
    the seek offset of the beginning of the content. Does not read body content into memory.
    """
    metadata_lines = []
    in_metadata = False
    prefix = ""
    end_pattern = FmFormat.yaml.end

    with open(file_path, "r") as f:
        try:
            first_line = f.readline().strip()
        except StopIteration:
            return None, 0

        if first_line == FmFormat.yaml.start:
            prefix = FmFormat.yaml.prefix
            in_metadata = True
        elif first_line == FmFormat.html.start:
            in_metadata = True
            prefix = FmFormat.html.prefix
            end_pattern = FmFormat.html.end
        elif first_line == FmFormat.code.start:
            in_metadata = True
            prefix = FmFormat.code.prefix
            end_pattern = FmFormat.code.end

        while True:
            line = f.readline()
            if not line:
                break
            if line.strip() == end_pattern and in_metadata:
                if prefix:
                    remove_prefix = lambda mline: (
                        mline[len(prefix) :] if mline.startswith(prefix) else mline
                    )
                else:
                    remove_prefix = lambda mline: mline
                metadata_str = "".join(remove_prefix(mline) for mline in metadata_lines)
                return metadata_str, f.tell()

            if in_metadata:
                metadata_lines.append(line)

        if in_metadata:  # If still true, it means the end '---' was never found
            raise FileFormatError(
                f"Error reading {file_path}: end of YAML front matter ('---') not found"
            )

    return None, 0


def fmf_read_raw(file_path: Path | str) -> Tuple[str, Optional[str]]:
    """
    Reads the full content and raw (unparsed) metadata from the file, both as strings.
    """
    metadata_str, offset = fmf_read_frontmatter(file_path)

    with open(file_path, "r") as f:
        f.seek(offset)
        content = f.read()

    return content, metadata_str


def fmf_strip_frontmatter(file_path: Path | str) -> None:
    """
    Strips the metadata frontmatter from the file. Does not read the content
    (except to do a file copy) so should work fairly quickly on large files.
    """
    _, offset = fmf_read_frontmatter(file_path)
    if offset > 0:
        temp_file_path = f"{file_path}.stripped.tmp"
        try:
            with open(file_path, "r") as original_file, open(temp_file_path, "w") as temp_file:
                original_file.seek(offset)
                shutil.copyfileobj(original_file, temp_file)
            os.replace(temp_file_path, file_path)
        except Exception as e:
            try:
                os.remove(temp_file_path)
            except FileNotFound:
                pass
            raise e


## Tests


def test_fmf_basic():
    os.makedirs("tmp", exist_ok=True)

    # Test with Markdown.
    file_path_md = "tmp/test_write.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_md, content_md, metadata_md)
    with open(file_path_md, "r") as f:
        lines = f.readlines()
    assert lines[0] == FmFormat.yaml.start + "\n"
    assert lines[-1].strip() == content_md
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading Markdown.
    file_path_md = "tmp/test_read.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_md, "w") as f:
        f.write(FmFormat.yaml.start + "\n")
        f.write("title: Test Title\n")
        f.write("author: Test Author\n")
        f.write(FmFormat.yaml.end + "\n")
        f.write(content_md)
    read_content_md, read_metadata_md = fmf_read(file_path_md)
    assert read_content_md.strip() == content_md
    assert read_metadata_md == metadata_md

    # Test with HTML.
    file_path_html = "tmp/test_write.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_html, content_html, metadata_html, format=FmFormat.html)
    with open(file_path_html, "r") as f:
        lines = f.readlines()
    assert lines[0] == FmFormat.html.start + "\n"
    assert lines[-1].strip() == content_html
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading HTML.
    file_path_html = "tmp/test_read.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_html, "w") as f:
        f.write(FmFormat.html.start + "\n")
        write_yaml(metadata_html, f)
        f.write(FmFormat.html.end + "\n")
        f.write(content_html)
    read_content_html, read_metadata_html = fmf_read(file_path_html)
    assert read_content_html.strip() == content_html
    assert read_metadata_html == metadata_html

    # Test with code frontmatter.
    file_path_code = "tmp/test_write_code.py"
    content_code = "print('Hello, World!')"
    metadata_code = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_code, content_code, metadata_code, format=FmFormat.code)
    with open(file_path_code, "r") as f:
        lines = f.readlines()
    assert lines[0] == FmFormat.code.start + "\n"
    assert lines[-1].strip() == content_code
    assert "# title: Test Title\n" in lines
    assert "# author: Test Author\n" in lines

    # Test reading code frontmatter.
    file_path_code = "tmp/test_read_code.py"
    content_code = "print('Hello, World!')"
    metadata_code = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_code, "w") as f:
        f.write(FmFormat.code.start + "\n")
        f.write("# title: Test Title\n")
        f.write("# author: Test Author\n")
        f.write(FmFormat.code.end + "\n")
        f.write(content_code)
    read_content_code, read_metadata_code = fmf_read(file_path_code)
    assert read_content_code.strip() == content_code
    assert read_metadata_code == metadata_code


def test_fmf_with_custom_key_sort():
    os.makedirs("tmp", exist_ok=True)

    # Test with Markdown.
    file_path_md = "tmp/test_write_custom_sort.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author", "date": "2022-01-01"}
    priority_keys = ["date", "title"]
    key_sort = custom_key_sort(priority_keys)
    fmf_write(file_path_md, content_md, metadata_md, key_sort=key_sort)
    with open(file_path_md, "r") as f:
        lines = f.readlines()
    assert lines[0] == FmFormat.yaml.start + "\n"
    assert lines[-1].strip() == content_md
    # Check that the priority keys come first in the order they are in the list
    assert lines[1].strip() == "date: '2022-01-01'"
    assert lines[2].strip() == "title: Test Title"
    assert lines[3].strip() == "author: Test Author"


def test_fmf_metadata():
    os.makedirs("tmp", exist_ok=True)

    # Test offset.
    file_path_md = "tmp/test_offset.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_md, content_md, metadata_md)
    result, offset = fmf_read_frontmatter(file_path_md)
    assert result == """author: Test Author\ntitle: Test Title\n"""
    assert offset == len(result) + 2 * (len("---") + 1)

    # Test a zero-length file.
    zero_length_file = "tmp/empty_file.txt"
    Path(zero_length_file).touch()

    result, offset = fmf_read_frontmatter(zero_length_file)
    assert (result, offset) == (None, 0)

    # Test stripping metadata from Markdown.
    file_path_md = "tmp/test_strip_metadata.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_md, content_md, metadata_md)
    fmf_strip_frontmatter(file_path_md)
    with open(file_path_md, "r") as f:
        stripped_content = f.read()
    assert stripped_content.strip() == content_md
