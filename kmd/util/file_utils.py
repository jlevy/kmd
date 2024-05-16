from pathlib import Path
import shutil
from typing import Optional
from strif import move_to_backup


def move_file(src: str, dest: str, backup_suffix: Optional[str] = "{timestamp}.bak"):
    """
    Move file, handling parent directory creation and optionally keeping a backup
    if the destination file already exists.
    """
    src_path = Path(src)
    dest_path = Path(dest)
    if backup_suffix:
        move_to_backup(dest_path, backup_suffix=backup_suffix)
    if dest_path.exists():
        raise FileExistsError(f"Destination file already exists: {dest}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src_path, dest_path)
