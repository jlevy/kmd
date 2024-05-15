import logging
import subprocess
import sys

log = logging.getLogger(__name__)


def view_file(file_path: str):
    """
    Displays a file in the console with pagination and syntax highlighting.
    """
    # TODO: Update this to handle YAML frontmatter more nicely.
    try:
        subprocess.run(f'pygmentize -g "{file_path}" | less -R', shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error displaying file: {e}", file=sys.stderr)
