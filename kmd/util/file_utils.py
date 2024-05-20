from pathlib import Path
import shutil
from strif import move_to_backup


def move_file(src: str, dest: str, keep_backup: bool = True):
    """
    Move file, handling parent directory creation and optionally keeping a backup
    if the destination file already exists.
    """
    src_path = Path(src)
    dest_path = Path(dest)
    if not keep_backup and dest_path.exists():
        raise FileExistsError(f"Destination file already exists: {dest}")
    if keep_backup and src_path.exists() and dest_path.exists():
        move_to_backup(dest, backup_suffix=".{timestamp}.bak")

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src_path, dest_path)
