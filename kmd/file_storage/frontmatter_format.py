"""
Frontmatter format: Read and write files with YAML frontmatter, to support metadata on text files.

Frontmatter can be either enclosed in `---` delimiters, as with Jekyll, or between
`<!---` and `--->` delimiters for convenience in text or HTML files. These markers must be
alone on their lines.
"""

from pathlib import Path
from typing import Tuple, Optional, Dict
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from strif import atomic_output_file


def fmf_write(file_path: Path | str, content: str, metadata: Optional[Dict]) -> None:
    """
    Write the given Markdown content to a file, with associated YAML metadata, in
    Jekyll-style frontmatter format.
    """

    yaml = YAML()

    with atomic_output_file(file_path, make_parents=True) as temp_output:
        with open(temp_output, "w") as f:
            if metadata:
                f.write("---\n")
                yaml.dump(metadata, f)
                f.write("---\n")

            f.write(content)


def fmf_read(file_path: Path | str) -> Tuple[str, Optional[Dict]]:
    """
    Read UTF-8 text content (typically Markdown) from a file with optional YAML metadata
    in Jekyll-style frontmatter format.
    """
    yaml = YAML()
    metadata = None
    content = []

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
    except UnicodeDecodeError as e:
        raise ValueError(f"File not a text file: {file_path}: {e}")
    except IOError as e:
        raise IOError(f"Error reading file {file_path}: {e}")

    if not lines:
        raise ValueError(f"File is empty: {file_path}")

    metadata_lines = []
    first_line = lines[0].strip()
    in_metadata = False
    end_pattern = "---"
    if first_line == "---":
        in_metadata = True
    elif first_line == "<!---":
        in_metadata = True
        end_pattern = "--->"

    start_index = 1 if in_metadata else 0

    for i in range(start_index, len(lines)):
        line = lines[i]
        if line.strip() == end_pattern and in_metadata:
            try:
                metadata = yaml.load("".join(metadata_lines))
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
