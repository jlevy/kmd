import os
from pathlib import Path
from typing import Tuple
from kmd.config import WORKSPACE_DIR
from kmd.file_storage.file_types import file_ext_for
from kmd.model.model import Item, ItemTypeEnum, item_type_to_folder
from kmd.file_storage.frontmatter_format import fmf_read, fmf_write

base_dir = Path(WORKSPACE_DIR)


def _filename_for(item: Item) -> str:
    # FIXME: Get from list of files and cache.
    taken_slugs = set()

    name = item.unique_slug(taken_slugs)
    type = item.type.value
    ext = file_ext_for(item).value

    # Suffix files with both item type and a suitable file extension.
    return name + "." + type + "." + ext


def _parse_filename(filename: str) -> Tuple[str, str, str]:
    parts = filename.rsplit(".", 2)
    if len(parts) != 3:
        raise ValueError(
            f"Filename does not match file store convention (name.type.ext): {filename}"
        )
    return parts[0], parts[1], parts[2]


def _type_from_filename(filename: str) -> ItemTypeEnum:
    _name, item_type, _ext = _parse_filename(filename)
    try:
        return ItemTypeEnum[item_type]
    except KeyError:
        raise ValueError(f"Unknown item type: {item_type}")


class FileStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def save(self, item: Item) -> str:
        folder_path = Path(item_type_to_folder(item.type))

        filename = _filename_for(item)
        store_path = folder_path / filename
        full_path = self.base_dir / store_path
        fmf_write(full_path, item.body_text(), item.metadata())

        # Set actual file creation and modification times if available.
        if item.created_at:
            created_time = item.created_at.timestamp()
            modified_time = item.modified_at.timestamp() if item.modified_at else created_time
            os.utime(full_path, (created_time, modified_time))

        return str(store_path)

    def load(self, store_path: str) -> Item:
        item_type = _type_from_filename(store_path)
        body, metadata = fmf_read(self.base_dir / store_path)
        if not metadata:
            raise ValueError(f"No metadata found in {store_path}")

        other_metadata = {
            key: value for key, value in metadata.items() if key not in ["body", "type"]
        }

        return Item(type=item_type, body=body, **other_metadata)


_file_store = FileStore(base_dir)


def load_item(store_path: str) -> Item:
    return _file_store.load(store_path)


def save_item(item: Item) -> str:
    return _file_store.save(item)
