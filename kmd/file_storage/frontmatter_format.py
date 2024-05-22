"""
Frontmatter format: Read and write files with YAML frontmatter, to support convenient
metadata on text files in a way that is compatible with browsers, editors, and Markdown
parsers.

Frontmatter can be either enclosed in `---` delimiters, as with Jekyll, or between
`<!---` and `--->` delimiters for convenience in text or HTML files. These markers must
be alone on their own lines.
"""

import os
from pathlib import Path
from typing import Tuple, Optional, Dict
from ruamel.yaml.error import YAMLError
from strif import atomic_output_file
from kmd.file_storage.yaml_util import from_yaml_string, write_yaml

YAML_SEPARATOR = "---"
HTML_FRONTMATTER_START = "<!---"
HTML_FRONTMATTER_END = "--->"


def fmf_write(
    file_path: Path | str, content: str, metadata: Optional[Dict], is_html: bool = False
) -> None:
    """
    Write the given Markdown content to a file, with associated YAML metadata, in
    Jekyll-style frontmatter format.
    """
    with atomic_output_file(file_path, make_parents=True) as temp_output:
        with open(temp_output, "w") as f:
            if metadata:
                f.write(HTML_FRONTMATTER_START) if is_html else f.write(YAML_SEPARATOR)
                f.write("\n")
                write_yaml(metadata, f)
                f.write(HTML_FRONTMATTER_END) if is_html else f.write(YAML_SEPARATOR)
                f.write("\n")

            f.write(content)


def fmf_read(file_path: Path | str) -> Tuple[str, Optional[Dict]]:
    """
    Read UTF-8 text content (typically Markdown) from a file with optional YAML metadata
    in Jekyll-style frontmatter format.
    """
    metadata = None
    content = []

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
    except UnicodeDecodeError as e:
        raise ValueError(f"File not a text file: {file_path}: {e}")

    if not lines:
        raise ValueError(f"File is empty: {file_path}")

    metadata_lines = []
    first_line = lines[0].strip()
    in_metadata = False
    end_pattern = YAML_SEPARATOR
    if first_line == YAML_SEPARATOR:
        in_metadata = True
    elif first_line == HTML_FRONTMATTER_START:
        in_metadata = True
        end_pattern = HTML_FRONTMATTER_END

    start_index = 1 if in_metadata else 0

    for i in range(start_index, len(lines)):
        line = lines[i]
        if line.strip() == end_pattern and in_metadata:
            try:
                metadata = from_yaml_string("".join(metadata_lines))
            except YAMLError as e:
                raise ValueError(f"Error parsing YAML metadata on {file_path}: {e}")
            in_metadata = False
            continue

        if in_metadata:
            metadata_lines.append(line)
        else:
            content.append(line)

    if in_metadata:  # If still true, it means the end '---' was never found
        raise ValueError(f"Error reading {file_path}: end of YAML front matter ('---') not found")

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
    assert lines[0] == YAML_SEPARATOR + "\n"
    assert lines[-1].strip() == content_md
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test with HTML.
    file_path_html = "tmp/test_write.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_html, content_html, metadata_html, is_html=True)
    with open(file_path_html, "r") as f:
        lines = f.readlines()
    assert lines[0] == HTML_FRONTMATTER_START + "\n"
    assert lines[-1].strip() == content_html
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading Markdown.
    file_path_md = "tmp/test_read.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_md, "w") as f:
        f.write(YAML_SEPARATOR + "\n")
        f.write("title: Test Title\n")
        f.write("author: Test Author\n")
        f.write(YAML_SEPARATOR + "\n")
        f.write(content_md)
    read_content_md, read_metadata_md = fmf_read(file_path_md)
    assert read_content_md.strip() == content_md
    assert read_metadata_md == metadata_md

    # Test reading HTML.
    file_path_html = "tmp/test_read.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_html, "w") as f:
        f.write(HTML_FRONTMATTER_START + "\n")
        write_yaml(metadata_html, f)
        f.write(HTML_FRONTMATTER_END + "\n")
        f.write(content_html)
    read_content_html, read_metadata_html = fmf_read(file_path_html)
    assert read_content_html.strip() == content_html
    assert read_metadata_html == metadata_html
