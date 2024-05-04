from pathlib import Path
from os.path import dirname
from kmd.config import WORKSPACE_DIR
from kmd.model.items import Item, folder_to_item_type, item_type_to_folder
from kmd.workspace.frontmatter_format import fmf_read, fmf_write

base_dir = Path(WORKSPACE_DIR)


class FileStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def save(self, item: Item) -> str:
        folder_path = Path(item_type_to_folder(item.type))
        # FIXME: Get from list of files and cache.
        taken_slugs = set()
        # FIXME: Handle other convenient suffixes in file_types.py.
        store_path = (folder_path / item.unique_slug(taken_slugs)).with_suffix(".md")
        fmf_write(self.base_dir / store_path, item.body_text(), item.metadata())
        return str(store_path)

    def load(self, path: str) -> Item:
        folder_name = dirname(path)
        item_type = folder_to_item_type(folder_name)
        body, metadata = fmf_read(self.base_dir / path)
        if not metadata:
            raise ValueError(f"No metadata found in {path}")

        other_metadata = {
            key: value for key, value in metadata.items() if key not in ["body", "type"]
        }

        return Item(type=item_type, body=body, **other_metadata)


_file_store = FileStore(base_dir)


def load_item(store_path: str) -> Item:
    return _file_store.load(store_path)


def save_item(item: Item) -> str:
    return _file_store.save(item)
