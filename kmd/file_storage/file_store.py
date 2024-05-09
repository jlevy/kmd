import logging
import os
from pathlib import Path
import textwrap
from typing import Optional, Tuple
from os.path import join
from os import path
import inflect

from slugify import slugify
from strif import copyfile_atomic
from kmd.config import WORKSPACE_DIR
from kmd.model.url import canonicalize_url
from kmd.model.locators import Locator, StorePath
from kmd.model.items_model import Format, Item, ItemType
from kmd.file_storage.frontmatter_format import fmf_read, fmf_write
from kmd.util.uniquifier import Uniquifier
from kmd.util.url_utils import Url, is_url


log = logging.getLogger(__name__)

# For folder names, note -> notes, question -> questions, etc.
_inflect = inflect.engine()
_type_to_folder = {name: _inflect.plural(name) for name, _value in ItemType.__members__.items()}  # type: ignore


def item_type_to_folder(item_type: ItemType) -> str:
    return _type_to_folder[item_type.name]


def _parse_filename(filename: str) -> Tuple[str, str, str]:
    parts = filename.rsplit(".", 2)
    if len(parts) != 3:
        raise ValueError(
            f"Filename does not match file store convention (name.type.ext): {filename}"
        )
    name, item_type, ext = parts
    return name, item_type, ext


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
    """
    Store items on the filesystem, using a simple convention for filenames and folders.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.uniquifier = Uniquifier()
        self._initialize_uniquifier()

        log.info("Using file store in %s (%s items)", base_dir, len(self.uniquifier))

    def _initialize_uniquifier(self):
        for _root, _dirs, files in os.walk(self.base_dir):
            for file in files:
                try:
                    name, item_type, ext = _parse_filename(file)
                except ValueError:
                    log.info("Skipping file with invalid name: %s", file)
                    continue
                self.uniquifier.uniquify(name, f"{item_type}.{ext}")

    def _filename_for(self, item: Item) -> str:
        """Get a suitable filename for this item that is close to the slugified title yet also unique."""

        title = item.get_title()
        slug = slugify(title, max_length=64, separator="_")

        # Get a unique name per item type.
        unique_slug = self.uniquifier.uniquify(slug, item.get_full_suffix())

        type = item.type.value
        ext = item.get_file_ext().value

        # Suffix files with both item type and a suitable file extension.
        return f"{unique_slug}.{type}.{ext}"

    def path_for(self, item: Item) -> Tuple[str, StorePath]:
        """Return (base_dir, store_path) for an item, which may or may not exist."""

        folder_path = Path(item_type_to_folder(item.type))
        filename = self._filename_for(item)
        store_path = folder_path / filename
        return str(self.base_dir), StorePath(str(store_path))

    def save(self, item: Item) -> StorePath:
        # Binary or large files must be referenced by path.
        # If external file alrady exists, the file is alrady saved (without metadata).
        if (
            item.external_path
            and path.exists(item.external_path)
            and path.commonpath([self.base_dir, item.external_path]) == str(self.base_dir)
        ):
            log.info("External file already saved: %s", item.external_path)
            store_path = StorePath(path.relpath(item.external_path, self.base_dir))
        else:
            # Otherwise it's still in memory or in a file outside the workspace and we need to save it.
            base_dir, store_path = self.path_for(item)
            full_path = join(base_dir, store_path)

            if item.external_path:
                copyfile_atomic(item.external_path, full_path)
            else:
                if item.is_binary:
                    raise ValueError(f"Binary Items should be external files: {item}")
                formatted_body = _format_text(item.body_text(), item.format)
                fmf_write(full_path, formatted_body, item.metadata())

            # Set filesystem file creation and modification times as well.
            if item.created_at:
                created_time = item.created_at.timestamp()
                modified_time = item.modified_at.timestamp() if item.modified_at else created_time
                os.utime(full_path, (created_time, modified_time))

        log.warn("Saved %s: %s", item.type.value, store_path)
        return store_path

    def load(self, store_path: StorePath) -> Item:
        item_type = _type_from_filename(store_path)
        body, metadata = fmf_read(self.base_dir / store_path)
        if not metadata:
            raise ValueError(f"No metadata found in {store_path}")

        other_metadata = {
            key: value for key, value in metadata.items() if key not in ["body", "type"]
        }

        return Item(type=item_type, body=body, **other_metadata)


# TODO: May want to have a settable current workspace directory but for now it's fixed.
workspace = FileStore(Path(WORKSPACE_DIR))


def locate_in_store(locator: Locator) -> Item:
    if is_url(locator):
        url = canonicalize_url(Url(locator))
        item = Item(ItemType.resource, url=url, format=Format.url)
        store_path = workspace.save(item)
        log.warn("Saved url: %s", store_path)
    else:
        item = workspace.load(StorePath(locator))

    return item
