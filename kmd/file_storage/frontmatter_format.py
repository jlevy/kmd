"""
Frontmatter format: Read and write files with YAML frontmatter, to support convenient
metadata on text files in a way that is compatible with browsers, editors, and Markdown
parsers.

Frontmatter can be either enclosed in `---` delimiters, as with Jekyll, or between
`<!---` and `--->` delimiters for convenience in text or HTML files. These markers must
be alone on their own lines.
"""

from enum import Enum
import os
from pathlib import Path
from typing import Tuple, Optional, Dict
from ruamel.yaml.error import YAMLError
from strif import atomic_output_file
from kmd.file_storage.yaml_util import (
    KeySort,
    custom_key_sort,
    from_yaml_string,
    to_yaml_string,
    write_yaml,
)
from kmd.model.errors_model import FileFormatError


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
    Write the given Markdown content to a file, with associated YAML metadata, in
    Jekyll-style frontmatter format.
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


def fmf_read(file_path: Path | str) -> Tuple[str, Optional[Dict]]:
    """
    Read UTF-8 text content (typically Markdown) from a file with optional YAML metadata
    in Jekyll-style frontmatter format. Auto-detects variant formats for HTML and code
    (Python style) based on whether the prefix is `---` or `<!---` or `#---`.
    """
    metadata = None
    content = []

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
    except UnicodeDecodeError as e:
        raise FileFormatError(f"File not a text file: {file_path}: {e}")

    if not lines:
        raise FileFormatError(f"File is empty: {file_path}")

    metadata_lines = []
    first_line = lines[0].strip()
    in_metadata = False
    prefix = ""
    end_pattern = FmFormat.yaml.end
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

    start_index = 1 if in_metadata else 0

    for i in range(start_index, len(lines)):
        line = lines[i]
        if line.strip() == end_pattern and in_metadata:
            try:
                if prefix:
                    remove_prefix = lambda mline: (
                        mline[len(prefix) :] if mline.startswith(prefix) else mline
                    )
                else:
                    remove_prefix = lambda mline: mline
                metadata_str = "".join(remove_prefix(mline) for mline in metadata_lines)
                metadata = from_yaml_string(metadata_str)
            except YAMLError as e:
                raise FileFormatError(f"Error parsing YAML metadata on {file_path}: {e}")
            in_metadata = False
            continue

        if in_metadata:
            metadata_lines.append(line)
        else:
            content.append(line)

    if in_metadata:  # If still true, it means the end '---' was never found
        raise FileFormatError(
            f"Error reading {file_path}: end of YAML front matter ('---') not found"
        )

    return "".join(content), metadata


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
