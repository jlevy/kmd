import shlex
import shutil
from pathlib import Path

from strif import move_to_backup

# TODO: Have a copy_to_backup function that always adds a backup suffix.


def move_file(src_path: Path, dest_path: Path, keep_backup: bool = True):
    """
    Move file, handling parent directory creation and optionally keeping a backup
    if the destination file already exists.
    """
    if not keep_backup and dest_path.exists():
        raise FileExistsError(f"Destination file already exists: {shlex.quote(str(dest_path))}")
    if keep_backup and src_path.exists() and dest_path.exists():
        move_to_backup(str(dest_path), backup_suffix=".{timestamp}.bak")

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src_path, dest_path)

    # TODO: If we created a backup, compare file contents and remove backup if it's identical, to avoid clutter.
