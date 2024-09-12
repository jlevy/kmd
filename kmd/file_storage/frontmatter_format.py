"""
Frontmatter format: Read and write files with YAML frontmatter, to support convenient
metadata on text files in a way that is compatible with browsers, editors, and Markdown
parsers.

Frontmatter can be either enclosed in `---` delimiters, as with Jekyll, or between
`<!---` and `--->` delimiters for convenience in text or HTML files. These markers must
be alone on their own lines.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

from ruamel.yaml.error import YAMLError
from strif import atomic_output_file

from kmd.file_formats.yaml_util import (
    custom_key_sort,
    from_yaml_string,
    KeySort,
    to_yaml_string,
    write_yaml,
)
from kmd.model.errors_model import FileFormatError
from kmd.text_formatting.text_formatting import fmt_path


class FmSyntax(Enum):
    """
    Markers used for frontmatter.
    """

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
    fm_synta: FmSyntax = FmSyntax.yaml,
    key_sort: Optional[KeySort] = None,
) -> None:
    """
    Write the given Markdown content to a file, with associated YAML metadata, in
    Jekyll-style frontmatter format.
    """
    with atomic_output_file(file_path, make_parents=True) as temp_output:
        with open(temp_output, "w") as f:
            if metadata:
                f.write(fm_synta.start)
                f.write("\n")
                for line in to_yaml_string(metadata, key_sort=key_sort).splitlines():
                    f.write(fm_synta.prefix + line)
                    f.write("\n")
                f.write(fm_synta.end)
                f.write("\n")

            f.write(content)


def fmf_read(file_path: Path | str) -> Tuple[str, Optional[Dict]]:
    """
    Read UTF-8 text content (typically Markdown) from a file with optional YAML metadata
    in Jekyll-style frontmatter format. Auto-detects variant formats for HTML and code
    (Python style) based on whether the prefix is `---` or `<!---` or `#---`.
    """
    content, metadata_str = fmf_read_raw(file_path)
    metadata = None
    if metadata_str:
        try:
            metadata = from_yaml_string(metadata_str)
        except YAMLError as e:
            raise FileFormatError(f"Error parsing YAML metadata: {fmt_path(file_path)}: {e}")
    return content, metadata


def fmf_read_metadata(file_path: Path | str) -> Tuple[Optional[str], int]:
    """
    Reads the metadata frontmatter from the file and returns the metadata string and
    the seek offset of the beginning of the content.
    """
    metadata_lines = []
    in_metadata = False
    prefix = ""
    end_pattern = FmSyntax.yaml.end

    with open(file_path, "r") as f:
        try:
            first_line = f.readline().strip()
        except StopIteration:
            return None, 0

        if first_line == FmSyntax.yaml.start:
            prefix = FmSyntax.yaml.prefix
            in_metadata = True
        elif first_line == FmSyntax.html.start:
            in_metadata = True
            prefix = FmSyntax.html.prefix
            end_pattern = FmSyntax.html.end
        elif first_line == FmSyntax.code.start:
            in_metadata = True
            prefix = FmSyntax.code.prefix
            end_pattern = FmSyntax.code.end

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
    Reads the raw content and metadata from the file.
    """
    metadata_str, offset = fmf_read_metadata(file_path)

    with open(file_path, "r") as f:
        f.seek(offset)
        content = f.read()

    return content, metadata_str


## Tests


def test_fmf():
    os.makedirs("tmp", exist_ok=True)

    # Test with Markdown.
    file_path_md = "tmp/test_write.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_md, content_md, metadata_md)
    with open(file_path_md, "r") as f:
        lines = f.readlines()
    assert lines[0] == FmSyntax.yaml.start + "\n"
    assert lines[-1].strip() == content_md
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading Markdown.
    file_path_md = "tmp/test_read.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_md, "w") as f:
        f.write(FmSyntax.yaml.start + "\n")
        f.write("title: Test Title\n")
        f.write("author: Test Author\n")
        f.write(FmSyntax.yaml.end + "\n")
        f.write(content_md)
    read_content_md, read_metadata_md = fmf_read(file_path_md)
    assert read_content_md.strip() == content_md
    assert read_metadata_md == metadata_md

    # Test with HTML.
    file_path_html = "tmp/test_write.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_html, content_html, metadata_html, fm_synta=FmSyntax.html)
    with open(file_path_html, "r") as f:
        lines = f.readlines()
    assert lines[0] == FmSyntax.html.start + "\n"
    assert lines[-1].strip() == content_html
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading HTML.
    file_path_html = "tmp/test_read.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_html, "w") as f:
        f.write(FmSyntax.html.start + "\n")
        write_yaml(metadata_html, f)
        f.write(FmSyntax.html.end + "\n")
        f.write(content_html)
    read_content_html, read_metadata_html = fmf_read(file_path_html)
    assert read_content_html.strip() == content_html
    assert read_metadata_html == metadata_html

    # Test with code frontmatter.
    file_path_code = "tmp/test_write_code.py"
    content_code = "print('Hello, World!')"
    metadata_code = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_code, content_code, metadata_code, fm_synta=FmSyntax.code)
    with open(file_path_code, "r") as f:
        lines = f.readlines()
    assert lines[0] == FmSyntax.code.start + "\n"
    assert lines[-1].strip() == content_code
    assert "# title: Test Title\n" in lines
    assert "# author: Test Author\n" in lines

    # Test reading code frontmatter.
    file_path_code = "tmp/test_read_code.py"
    content_code = "print('Hello, World!')"
    metadata_code = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_code, "w") as f:
        f.write(FmSyntax.code.start + "\n")
        f.write("# title: Test Title\n")
        f.write("# author: Test Author\n")
        f.write(FmSyntax.code.end + "\n")
        f.write(content_code)
    read_content_code, read_metadata_code = fmf_read(file_path_code)
    assert read_content_code.strip() == content_code
    assert read_metadata_code == metadata_code

    # Test offset.
    file_path_md = "tmp/test_offset.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_md, content_md, metadata_md)
    result, offset = fmf_read_metadata(file_path_md)
    assert result == """author: Test Author\ntitle: Test Title\n"""
    assert offset == len(result) + 2 * (len("---") + 1)

    # Test a zero-length file.
    zero_length_file = "tmp/empty_file.txt"
    Path(zero_length_file).touch()

    result, offset = fmf_read_metadata(zero_length_file)
    assert (result, offset) == (None, 0)


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
    assert lines[0] == FmSyntax.yaml.start + "\n"
    assert lines[-1].strip() == content_md
    # Check that the priority keys come first in the order they are in the list
    assert lines[1].strip() == "date: '2022-01-01'"
    assert lines[2].strip() == "title: Test Title"
    assert lines[3].strip() == "author: Test Author"
