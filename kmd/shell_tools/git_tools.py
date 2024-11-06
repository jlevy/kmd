from pathlib import Path
from typing import List


def add_to_git_ignore(dir: Path, pat_list: List[str]) -> None:
    """
    Add patterns to the .gitignore file for the given directory.
    """

    ignore_file = dir / ".gitignore"
    existing_lines = ignore_file.read_text().splitlines()
    with open(ignore_file, "a") as f:
        for pat in pat_list:
            if pat not in existing_lines:
                f.write(f"{pat}\n")
