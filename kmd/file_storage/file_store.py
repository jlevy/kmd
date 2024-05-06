import os
from pathlib import Path
import textwrap
from typing import Optional, Tuple
from kmd.config import WORKSPACE_DIR
from kmd.file_storage.file_types import file_ext_for
from kmd.model.model import Format, Item, ItemType, item_type_to_folder
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


def _type_from_filename(filename: str) -> ItemType:
    _name, item_type, _ext = _parse_filename(filename)
    try:
        return ItemType[item_type]
    except KeyError:
        raise ValueError(f"Unknown item type: {item_type}")


def _format_text(text: str, format: Optional[Format] = None, width=80) -> str:
    """
    When saving clean text of a known format, wrap it for readability.
    """
    if format == Format.plaintext:
        paragraphs = text.split("\n\n")
        wrapped_paragraphs = [
            textwrap.fill(p, width=width, break_long_words=False, replace_whitespace=False)
            for p in paragraphs
        ]
        return "\n\n".join(wrapped_paragraphs)
    # TODO: Add cleaner canonicalization/wrapping for Markdown.
    else:
        return text


class FileStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def save(self, item: Item) -> str:
        folder_path = Path(item_type_to_folder(item.type))

        filename = _filename_for(item)
        store_path = folder_path / filename
        full_path = self.base_dir / store_path
        formatted_body = _format_text(item.body_text(), item.format)
        fmf_write(full_path, formatted_body, item.metadata())

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
