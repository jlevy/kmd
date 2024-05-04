"""
Read and write files with Jekyll-style YAML frontmatter, to support metadata on text files.
"""

from pathlib import Path
from typing import Tuple, Optional, Dict
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from strif import atomic_output_file

# TODO: Add support for HTML-compatible frontmatter, using <!--- and --->.


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
    Read text content (typically Markdown) from a file with associated YAML metadata
    in Jekyll-style frontmatter format.
    """
    yaml = YAML()
    metadata = None
    content = []

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
    except IOError as e:
        raise IOError(f"Error reading file {file_path}: {e}")

    if not lines:
        return "", None

    metadata_lines = []
    in_metadata = lines[0].strip() == "---"
    start_index = 1 if in_metadata else 0

    for i in range(start_index, len(lines)):
        line = lines[i]
        if line.strip() == "---" and in_metadata:
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
