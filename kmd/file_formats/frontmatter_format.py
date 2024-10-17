"""
FRONTMATTER FORMAT

Simple, readable metadata attached to files can be useful in numerous
situations. Unfortunately, it's rarely clear how to store such metadata
in a consistent way across different kinds of files, that does not break
interoperability with existing tools.

Frontmatter format is a set of conventions to read and write metadata on
many kinds of files in a way that is broadly compatible with programming
languages, browsers, editors, Markdown parsers, and other tools.

Frontmatter format is a generalization of the common format for frontmatter
used by Jekyll and other CMSs for Markdown files. In that foramt, frontmatter
is enclosed in `---` delimiters.

Frontmatter format is a way to add metadata as frontmatter on any file.
In this generalized format, we allow multiple styles of frontmatter
demarcation, allowing for easy auto-detection, parsing, and compatibility.

Below are a few examples to illustrate:

---
title: Sample Markdown File
state: draft
created_at: 2022-08-07 00:00:00
tags:
  - yaml
  - examples
---
Hello, *World*!

<!---
title: Sample HTML File
--->
Hello, <i>World</i>!

#---
# author: Jane Doe
# description: A sample Python script
#---
print("Hello, World!")

/*---
filename: styles.css
---*/
.hello {
  color: green;
}

----
-- title: Sample SQL Script
----
SELECT * FROM world;


The full set of supported frontmatter styles are:

1. YAML: delimiters `---` and `---` with no prefix on each line.
   Useful for text or Markdown content.
2. HTML: delimiters `<!---` and `--->` with no prefix on each line.
   Useful for HTML or XML or similar content.
3. Hash: delimiters `#---` and `#---` with `# ` prefix on each line.
   Useful for Python or similar code content. Also works for CSV files with many tools.
4. Slash: delimiters `//---` and `//---` with `// ` prefix on each line
   Useful for Rust or C++ or similar code content.
5. Slash-star: delimiters `/*---` and `---*/` with no prefix on each line
   Useful for CSS or C or similar code content.
6. Dash: delimiters `----` and `----` with `-- ` prefix on each line
   Useful for SQL or similar code content.

The delimiters must be alone on their own lines, terminated with a newline.

Any style is acceptable on any file as it can be automatically detected.
When writing, you can specify the style.

For all frontmatter styles, the content between the delimiters can be any
text in UTF-8 encoding. But it is recommended to use YAML.

For some of the formats, each frontmatter line is prefixed with a prefix
to make sure the entire file remains valid in a given syntax (Python,
Rust, SQL, etc.). This prefix is stripped during parsing.

It is recommended to use a prefix with a trailing space (such as `# `)
but a bare prefix without the trailing space is also allowed. Other
whitespace is perserved (before parsing with YAML).

There is no restriction on the content of the file after the frontmatter.
It may even contain other content in frontmatter format, but this will
not be parsed as frontmatter. Typically, it is text, but it could be
binary as well.

Frontmatter is optional. This means almost any text file can be read as
frontmatter format.

This is a simple Python reference implementation. It auto-detects all the
frontmatter styles above. It supports reading small files easily into memory,
but also allows extracting or changing frontmatter without reading an entire
file. YAML parsing is automatic but not required. For readability, there
is also support for preferred sorting of YAML keys.
"""

import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Any, cast, Dict, List, Optional, Tuple

from ruamel.yaml.error import YAMLError

from kmd.file_formats.yaml_util import (
    custom_key_sort,
    from_yaml_string,
    KeySort,
    to_yaml_string,
    write_yaml,
)


class FileFormatError(ValueError):
    """
    Error for file format issues.
    """


class FmStyle(Enum):
    """
    The style of frontmatter demarcation to use.
    """

    # start, end, prefix, strip_prefixes
    yaml = ("---", "---", "", [])
    html = ("<!---", "--->", "", [])
    hash = ("#---", "#---", "# ", ["# ", "#"])
    slash = ("//---", "//---", "// ", ["// ", "//"])
    slash_star = ("/*---", "---*/", "", [])
    dash = ("----", "----", "-- ", ["-- ", "--"])

    @property
    def start(self) -> str:
        return self.value[0]

    @property
    def end(self) -> str:
        return self.value[1]

    @property
    def prefix(self) -> str:
        return self.value[2]

    @property
    def strip_prefixes(self) -> List[str]:
        return self.value[3]

    def strip_prefix(self, line: str) -> str:
        for prefix in self.strip_prefixes:
            if line.startswith(prefix):
                return line[len(prefix) :]
        return line


Metadata = Dict[str, Any]
"""
Parsed metadata from frontmatter.
"""


def fmf_write(
    path: Path | str,
    content: str,
    metadata: Optional[Metadata | str],
    style: FmStyle = FmStyle.yaml,
    key_sort: Optional[KeySort] = None,
    make_parents: bool = True,
) -> None:
    """
    Write the given Markdown text content to a file, with associated YAML metadata, in a
    generalized Jekyll-style frontmatter format. Metadata can be a raw string or a dict
    that will be serialized to YAML.
    """
    if isinstance(metadata, str):
        frontmatter_str = metadata
    else:
        frontmatter_str = to_yaml_string(metadata, key_sort=key_sort)

    path = Path(path)
    if make_parents and path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = f"{path}.fmf.write.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            if metadata:
                f.write(style.start)
                f.write("\n")
                for line in frontmatter_str.splitlines():
                    f.write(style.prefix + line)
                    f.write("\n")
                f.write(style.end)
                f.write("\n")

            f.write(content)
        os.replace(tmp_path, path)
    except Exception as e:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass
        raise e


def fmf_read(path: Path | str) -> Tuple[str, Optional[Metadata]]:
    """
    Read UTF-8 text content (typically Markdown) from a file with optional YAML metadata
    in Jekyll-style frontmatter format. Auto-detects variant formats for HTML and code
    (Python style) based on whether the prefix is `---` or `<!---` or `#---`.
    Reads the entire file into memory. Parses the metadata as YAML.
    """
    content, metadata_str = fmf_read_raw(path)
    metadata = None
    if metadata_str:
        try:
            metadata = from_yaml_string(metadata_str)
        except YAMLError as e:
            raise FileFormatError(f"Error parsing YAML metadata: `{path}`: {e}") from e
        if not isinstance(metadata, dict):
            raise FileFormatError(f"Invalid metadata type: {type(metadata)}")
        metadata = cast(Metadata, metadata)
    return content, metadata


def fmf_read_raw(path: Path | str) -> Tuple[str, Optional[str]]:
    """
    Reads the full content and raw (unparsed) metadata from the file, both as strings.
    """
    metadata_str, offset = fmf_read_frontmatter_raw(path)

    with open(path, "r", encoding="utf-8") as f:
        f.seek(offset)
        content = f.read()

    return content, metadata_str


def fmf_read_frontmatter_raw(path: Path | str) -> Tuple[Optional[str], int]:
    """
    Reads the metadata frontmatter from the file and returns the metadata string and
    the seek offset of the beginning of the content. Does not parse the metadata.
    Does not read the body content into memory.
    """
    metadata_lines = []
    in_metadata = False

    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline().rstrip()

        if first_line == FmStyle.yaml.start:
            delimiters = FmStyle.yaml
            in_metadata = True
        elif first_line == FmStyle.html.start:
            delimiters = FmStyle.html
            in_metadata = True
        elif first_line == FmStyle.hash.start:
            delimiters = FmStyle.hash
            in_metadata = True
        else:
            # Empty file or no recognized frontmatter.
            return None, 0

        while True:
            line = f.readline()
            if not line:
                break

            if line.rstrip() == delimiters.end and in_metadata:
                metadata_str = "".join(delimiters.strip_prefix(mline) for mline in metadata_lines)
                return metadata_str, f.tell()

            if in_metadata:
                metadata_lines.append(line)

        if in_metadata:  # If still true, the end delimiter was never found
            raise FileFormatError(
                f"Delimiter `{delimiters.end}` for end of frontmatter not found: `{(path)}`"
            )

    return None, 0


def fmf_strip_frontmatter(path: Path | str) -> None:
    """
    Strip the metadata frontmatter from the file, in place on the file.
    Does not read the content (except to do a file copy) so should work fairly
    quickly on large files. Does nothing if there is no frontmatter.
    """
    _, offset = fmf_read_frontmatter_raw(path)
    if offset > 0:
        tmp_path = f"{path}.fmf.strip.tmp"
        try:
            with open(path, "r", encoding="utf-8") as original_file, open(
                tmp_path, "w", encoding="utf-8"
            ) as temp_file:
                original_file.seek(offset)
                shutil.copyfileobj(original_file, temp_file)
            os.replace(tmp_path, path)
        except Exception as e:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            raise e


def fmf_insert_frontmatter(
    path: Path | str,
    metadata: Optional[Metadata],
    fm_style: FmStyle = FmStyle.yaml,
    key_sort: Optional[KeySort] = None,
) -> None:
    """
    Insert metadata as frontmatter into the given file, inserting at the top
    and replacing any existing frontmatter.
    """
    if metadata is None:
        return

    if isinstance(metadata, str):
        frontmatter_str = metadata
    else:
        frontmatter_str = to_yaml_string(metadata, key_sort=key_sort)

    # Prepare the new frontmatter.
    frontmatter_lines = [fm_style.start + "\n"]
    if frontmatter_str:
        for line in frontmatter_str.splitlines():
            frontmatter_lines.append(fm_style.prefix + line + "\n")
    frontmatter_lines.append(fm_style.end + "\n")

    tmp_path = f"{path}.fmf.insert.tmp"

    try:
        # Determine where any existing frontmatter ends (offset).
        _, offset = fmf_read_frontmatter_raw(path)

        with open(tmp_path, "w", encoding="utf-8") as temp_file:
            temp_file.writelines(frontmatter_lines)

            with open(path, "r", encoding="utf-8") as original_file:
                original_file.seek(offset)
                shutil.copyfileobj(original_file, temp_file)

        os.replace(tmp_path, path)
    except Exception as e:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
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
    assert lines[0] == FmStyle.yaml.start + "\n"
    assert lines[-1].strip() == content_md
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading Markdown.
    file_path_md = "tmp/test_read.md"
    content_md = "Hello, World!"
    metadata_md = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_md, "w") as f:
        f.write(FmStyle.yaml.start + "\n")
        f.write("title: Test Title\n")
        f.write("author: Test Author\n")
        f.write(FmStyle.yaml.end + "\n")
        f.write(content_md)
    read_content_md, read_metadata_md = fmf_read(file_path_md)
    assert read_content_md.strip() == content_md
    assert read_metadata_md == metadata_md

    # Test with HTML.
    file_path_html = "tmp/test_write.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_html, content_html, metadata_html, style=FmStyle.html)
    with open(file_path_html, "r") as f:
        lines = f.readlines()
    assert lines[0] == FmStyle.html.start + "\n"
    assert lines[-1].strip() == content_html
    assert "title: Test Title\n" in lines
    assert "author: Test Author\n" in lines

    # Test reading HTML.
    file_path_html = "tmp/test_read.html"
    content_html = "<p>Hello, World!</p>"
    metadata_html = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_html, "w") as f:
        f.write(FmStyle.html.start + "\n")
        write_yaml(metadata_html, f)
        f.write(FmStyle.html.end + "\n")
        f.write(content_html)
    read_content_html, read_metadata_html = fmf_read(file_path_html)
    assert read_content_html.strip() == content_html
    assert read_metadata_html == metadata_html

    # Test with code frontmatter.
    file_path_code = "tmp/test_write_code.py"
    content_code = "print('Hello, World!')"
    metadata_code = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path_code, content_code, metadata_code, style=FmStyle.hash)
    with open(file_path_code, "r") as f:
        lines = f.readlines()
    assert lines[0] == FmStyle.hash.start + "\n"
    assert lines[-1].strip() == content_code
    assert "# title: Test Title\n" in lines
    assert "# author: Test Author\n" in lines

    # Test reading code frontmatter.
    file_path_code = "tmp/test_read_code.py"
    content_code = "print('Hello, World!')"
    metadata_code = {"title": "Test Title", "author": "Test Author"}
    with open(file_path_code, "w") as f:
        f.write(FmStyle.hash.start + "\n")
        f.write("# title: Test Title\n")
        f.write("# author: Test Author\n")
        f.write(FmStyle.hash.end + "\n")
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
    assert lines[0] == FmStyle.yaml.start + "\n"
    assert lines[-1].strip() == content_md
    # Check that the priority keys come first in the order they are in the list
    assert lines[1].strip() == "date: '2022-01-01'"
    assert lines[2].strip() == "title: Test Title"
    assert lines[3].strip() == "author: Test Author"


def test_fmf_metadata():
    os.makedirs("tmp", exist_ok=True)

    # Test offset.
    file_path = "tmp/test_offset.md"
    content = "Hello, World!"
    metadata = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path, content, metadata)
    result, offset = fmf_read_frontmatter_raw(file_path)
    assert result == """title: Test Title\nauthor: Test Author\n"""
    assert offset == len(result) + 2 * (len("---") + 1)

    # Test a zero-length file.
    zero_length_file = "tmp/empty_file.txt"
    Path(zero_length_file).touch()

    result, offset = fmf_read_frontmatter_raw(zero_length_file)
    assert (result, offset) == (None, 0)

    # Test stripping metadata from Markdown.
    file_path = "tmp/test_strip_metadata.md"
    content = "Hello, World!"
    metadata = {"title": "Test Title", "author": "Test Author"}
    fmf_write(file_path, content, metadata)
    fmf_strip_frontmatter(file_path)
    with open(file_path, "r") as f:
        stripped_content = f.read()
    assert stripped_content.strip() == content

    # Test inserting metadata into a file without frontmatter.
    file_path = "tmp/test_insert_no_frontmatter.md"
    content = "Hello, World!"
    metadata = {"title": "Test Title", "author": "Test Author"}
    with open(file_path, "w") as f:
        f.write(content)
    fmf_insert_frontmatter(file_path, metadata)
    new_content, new_metadata = fmf_read(file_path)
    assert new_metadata == metadata
    assert new_content == content
    # Overwrite the existing metadata.
    metadata2 = {"something": "else"}
    fmf_insert_frontmatter(file_path, metadata2)
    new_content, new_metadata = fmf_read(file_path)
    assert new_metadata == metadata2
    assert new_content == content
