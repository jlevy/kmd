import os
from pathlib import Path
import textwrap
from typing import Any, Optional, Tuple
from os.path import join, relpath, commonpath
from os import path

from slugify import slugify
from strif import copyfile_atomic
from kmd.file_storage.filenames import parse_filename
from kmd.file_storage.yaml_util import read_yaml_file, write_yaml_file
from kmd.model.locators import StorePath
from kmd.model.items_model import FileExt, Format, Item, ItemType
from kmd.file_storage.frontmatter_format import fmf_read, fmf_write
from kmd.model.url import canonicalize_url
from kmd.util.file_utils import move_file
from kmd.util.type_utils import not_none
from kmd.util.uniquifier import Uniquifier
from kmd.util.text_formatting import plural
from kmd.util.url_utils import Url, is_url
from kmd.config.logger import get_logger

log = get_logger(__name__)

# For folder names, note -> notes, question -> questions, etc.
_type_to_folder = {name: plural(name) for name, _value in ItemType.__members__.items()}


def item_type_to_folder(item_type: ItemType) -> str:
    return _type_to_folder[item_type.name]


def _parse_check_filename(filename: str) -> Tuple[str, ItemType, FileExt]:
    dirname, name, item_type, ext = parse_filename(filename, expect_type_ext=True)
    try:
        return name, ItemType[item_type], FileExt[ext]
    except KeyError as e:
        raise ValueError(f"Unknown type or extension for file: {filename}: {e}")


def _format_from_ext(file_ext: FileExt) -> Optional[Format]:
    file_ext_to_format = {
        FileExt.html: Format.html,
        FileExt.md: Format.markdown,
        FileExt.txt: Format.plaintext,
        FileExt.pdf: Format.pdf,
        FileExt.yml: None,  # We will need to look at a YAML file to determine format.
    }
    return file_ext_to_format[file_ext]


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
    # TODO: Add cleaner canonicalization/wrapping for Markdown. Also Flowmark?
    else:
        return text


class PersistedYaml:
    """
    Maintain a value (such as a dictionary or list of strings) as a YAML file.
    """

    def __init__(self, filename: str, value: Any):
        self.filename = filename
        self.value = value

    def read(self) -> Any:
        return read_yaml_file(self.filename)

    def set(self, value: Any):
        write_yaml_file(value, self.filename)

    def remove(self, target: Any):
        """
        Remove all occurrences of the target value from the data structure.
        """

        def remove_value(data: Any, target: Any) -> Any:
            if isinstance(data, dict):
                return {k: remove_value(v, target) for k, v in data.items() if v != target}
            elif isinstance(data, list):
                return [remove_value(item, target) for item in data if item != target]
            elif data == target:
                return None
            else:
                return data

        self.value = remove_value(self.value, target)
        self.set(self.value)


class NoSelectionError(RuntimeError):
    pass


ARCHIVE_DIR = ".archive"
SETTINGS_DIR = ".settings"


class FileStore:
    """
    Store items on the filesystem, using a simple convention for filenames and folders.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.uniquifier = Uniquifier()
        self.url_map = {}
        self._initialize_index()

        self.archive_dir = join(self.base_dir, ARCHIVE_DIR)
        os.makedirs(self.archive_dir, exist_ok=True)
        self.settings_dir = join(self.base_dir, SETTINGS_DIR)
        os.makedirs(self.settings_dir, exist_ok=True)

        self.selection = PersistedYaml(join(self.settings_dir, "selection.yaml"), [])

    def _initialize_index(self):
        for root, _dirnames, filenames in os.walk(self.base_dir):
            for filename in filenames:
                store_path = StorePath(path.relpath(join(root, filename), self.base_dir))
                self._index_item(store_path)

    def _index_item(self, store_path: StorePath):
        """
        Update metadata index with a new item.
        """
        try:
            name, item_type, file_ext = _parse_check_filename(store_path)
        except ValueError:
            log.info("Skipping file with invalid name: %s", store_path)
            return
        self.uniquifier.add(name, f"{item_type.name}.{file_ext.name}")

        item = self.load(store_path)
        if item.url:
            self.url_map[item.url] = store_path

    def _new_filename_for(self, item: Item) -> str:
        """
        Get a suitable filename for this item that is close to the slugified title yet also unique.
        """
        title = item.get_title()
        slug = slugify(title, max_length=64, separator="_")

        # Get a unique name per item type.
        unique_slug = self.uniquifier.uniquify(slug, item.get_full_suffix())

        type = item.type.value
        ext = item.get_file_ext().value

        # Suffix files with both item type and a suitable file extension.
        return f"{unique_slug}.{type}.{ext}"

    def find_path_for(self, item: Item) -> Tuple[str, StorePath]:
        """
        Return (base_dir, store_path) for an item. Store path may or may not already exist, depending
        on whether store_path is already set on the item or the same item has been saved before.
        """
        if item.store_path:
            store_path = item.store_path
        elif item.url and item.format == Format.url and item.url in self.url_map:
            # If the item is a URL and we've already saved it, use the same store path.
            store_path = self.url_map[item.url]
            log.message("URL already saved: %s holds %s", store_path, item.url)
        else:
            folder_path = Path(item_type_to_folder(item.type))
            filename = self._new_filename_for(item)
            store_path = folder_path / filename
        return str(self.base_dir), StorePath(str(store_path))

    def save(self, item: Item) -> StorePath:
        """
        Save the item. Uses the store_path if it's already set or generates a new one.
        Updates item.store_path.
        """
        # If external file alrady exists within the workspace, the file is alrady saved (without metadata).
        if (
            item.external_path
            and path.exists(item.external_path)
            and path.commonpath([self.base_dir, item.external_path]) == str(self.base_dir)
        ):
            log.info("External file already saved: %s", item.external_path)
            store_path = StorePath(path.relpath(item.external_path, self.base_dir))
        else:
            # Otherwise it's still in memory or in a file outside the workspace and we need to save it.
            base_dir, store_path = self.find_path_for(item)
            full_path = join(base_dir, store_path)
            log.info("Saving item to %s: %s", full_path, item)

            # If we're overwriting an existing file, archive it first.
            if path.exists(full_path):
                try:
                    self.archive(store_path)
                except Exception as e:
                    log.warning("Error archiving existing file: %s", e)

            # Now save the new item.
            try:
                if item.external_path:
                    copyfile_atomic(item.external_path, full_path)
                else:
                    if item.is_binary:
                        raise ValueError(f"Binary Items should be external files: {item}")
                    formatted_body = _format_text(item.body_text(), item.format)
                    fmf_write(full_path, formatted_body, item.metadata())
            except IOError as e:
                log.error("Error saving item: %s", e)
                self.unarchive(store_path)

            # Set filesystem file creation and modification times as well.
            if item.created_at:
                created_time = item.created_at.timestamp()
                modified_time = item.modified_at.timestamp() if item.modified_at else created_time
                os.utime(full_path, (created_time, modified_time))

        item.store_path = store_path
        self._index_item(store_path)

        log.message("Saved %s: %s", item.type.value, store_path)
        return store_path

    def load(self, store_path: StorePath) -> Item:
        """
        Load item at the given path.
        """
        _name, item_type, file_ext = _parse_check_filename(store_path)
        format = _format_from_ext(file_ext)
        if FileExt.is_text(file_ext):
            # This is a known text format or a YAML file, so we can read the whole thing.
            body, metadata = fmf_read(self.base_dir / store_path)
            if not metadata:
                raise ValueError(f"No metadata found in file: {store_path}")

            other_metadata = {
                key: value for key, value in metadata.items() if key not in ["body", "type"]
            }

            return Item(type=item_type, body=body, **other_metadata, store_path=store_path)
        else:
            # This is a PDF or other binary file, so we just return the metadata.
            return Item(
                type=item_type,
                external_path=str(self.base_dir / store_path),
                format=not_none(format),
                file_ext=file_ext,
                store_path=store_path,
            )

    def add_resource(self, file_path_or_url: str) -> StorePath:
        """
        Add a resource from a file or URL.
        """
        if is_url(file_path_or_url):
            url = canonicalize_url(Url(file_path_or_url))
            item = Item(ItemType.resource, url=url, format=Format.url)
            # TODO: Also fetch the title and description as a follow-on action.
            return self.save(item)
        else:
            file_path = file_path_or_url
            try:
                _dirname, name, _item_type, ext_str = parse_filename(file_path)
                file_ext = FileExt(ext_str)
            except ValueError:
                raise ValueError(
                    f"Unknown extension for file: {file_path} (known types are {FileExt.__members__})"
                )
            format = Format.for_file_ext(file_ext)
            if not format:
                raise ValueError(f"Unknown format for file: {file_path}")

            with open(file_path, "r") as file:
                body = file.read()

            new_item = Item(
                type=ItemType.resource,
                title=name,
                file_ext=file_ext,
                format=format,
                body=body,
            )
            saved_store_path = self.save(new_item)
            return saved_store_path

    def _remove_references(self, store_path: StorePath):
        self.selection.remove(store_path)

    def archive(self, store_path: StorePath) -> StorePath:
        """
        Archive the item by moving it into the archive directory.
        """
        archive_path = join(self.archive_dir, store_path)
        move_file(
            join(self.base_dir, store_path),
            archive_path,
        )
        self._remove_references(store_path)
        return StorePath(join(ARCHIVE_DIR, store_path))

    def unarchive(self, store_path: StorePath):
        """
        Unarchive the item by moving back out of the archive directory.
        Path may be with or without the archive dir prefix.
        """
        if commonpath([ARCHIVE_DIR, store_path]) == ARCHIVE_DIR:
            store_path = StorePath(relpath(store_path, ARCHIVE_DIR))
        original_path = join(self.base_dir, store_path)
        move_file(
            join(self.archive_dir, store_path),
            original_path,
        )
        return StorePath(store_path)

    def set_selection(self, selection: list[StorePath]):
        self.selection.set(selection)

    def get_selection(self) -> list[StorePath]:
        try:
            return self.selection.read()
        except OSError:
            raise NoSelectionError()

    def unselect(self, unselect_paths: list[StorePath]):
        current_selection = self.get_selection()
        new_selection = [path for path in current_selection if path not in unselect_paths]
        self.set_selection(new_selection)
        return new_selection
