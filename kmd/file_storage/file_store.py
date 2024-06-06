import os
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple
from os.path import join, relpath, commonpath
from os import path
from slugify import slugify
from strif import copyfile_atomic
from kmd.config.text_styles import EMOJI_SUCCESS, EMOJI_WARN
from kmd.file_storage.filenames import parse_filename
from kmd.file_storage.persisted_yaml import PersistedYaml
from kmd.file_storage.yaml_util import custom_key_sort
from kmd.model.errors_model import InvalidStoreState
from kmd.model.locators import StorePath
from kmd.model.items_model import ITEM_FIELDS, FileExt, Format, Item, ItemId, ItemType
from kmd.file_storage.frontmatter_format import fmf_read, fmf_write
from kmd.model.canon_url import canonicalize_url
from kmd.text_handling.text_formatting import format_lines
from kmd.text_handling.doc_formatting import normalize_formatting
from kmd.text_handling.inflection import plural
from kmd.util.file_utils import move_file
from kmd.util.type_utils import not_none
from kmd.util.uniquifier import Uniquifier
from kmd.util.url import Url, is_url
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


def skippable_file(filename: str) -> bool:
    """
    Check if a file should be skipped when processing a directory.
    This skipps .archive, .settings, etc.
    """
    return len(filename) > 1 and filename.startswith(".")




ARCHIVE_DIR = ".archive"
SETTINGS_DIR = ".settings"

FILENAME_SLUG_MAX_LEN = 64

ITEM_FIELD_SORT = custom_key_sort(ITEM_FIELDS)


class FileStore:
    """
    Store items on the filesystem, using a simple convention for filenames and folders.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.uniquifier = Uniquifier()
        self.id_map: dict[ItemId, StorePath] = {}
        self._initialize_index()

        self.archive_dir = self.base_dir / ARCHIVE_DIR
        os.makedirs(self.archive_dir, exist_ok=True)
        self.settings_dir = self.base_dir / SETTINGS_DIR
        os.makedirs(self.settings_dir, exist_ok=True)

        # TODO: Store historical selections too. So if you run two commands you can go back to previous outputs.
        self.selection = PersistedYaml(self.settings_dir / "selection.yaml", init_value=[])

        self.action_params = PersistedYaml(self.settings_dir / "action_params.yaml", init_value={})

        self.log_store_info()

    def _initialize_index(self):
        num_dups = 0
        for root, dirnames, filenames in os.walk(self.base_dir):
            dirnames[:] = [d for d in dirnames if not skippable_file(d)]
            for filename in filenames:
                if not skippable_file(filename):
                    store_path = StorePath(path.relpath(join(root, filename), self.base_dir))
                    dup_path = self._index_item(store_path)
                    if dup_path:
                        num_dups += 1

        if num_dups > 0:
            log.warning("%s Found %s duplicate items in store. See kmd.log for details.", EMOJI_WARN, num_dups)

    def _index_item(self, store_path: StorePath) -> Optional[StorePath]:
        """
        Update metadata index with a new item.
        """
        try:
            name, item_type, file_ext = _parse_check_filename(store_path)
        except ValueError:
            log.debug("Skipping file with invalid name: %s", store_path)
            return
        self.uniquifier.add(name, f"{item_type.name}.{file_ext.name}")

        item = self.load(store_path)
        item_id = item.item_id()
        dup_path = None
        if item_id:
            old_path = self.id_map.get(item_id)
            if old_path:
                dup_path = old_path
                log.info("Duplicate items (%s):\n%s", item_id, format_lines([old_path, store_path]))
            self.id_map[item_id] = store_path

        return dup_path

    def _unindex_item(self, store_path: StorePath):
        """
        Remove an item from the metadata index.
        """
        try:
            item = self.load(store_path)
            item_id = item.item_id()
            if item_id:
                try:
                    self.id_map.pop(item_id, None)
                except KeyError:
                    pass  # If we happen to reload a store it might no longer be in memory.
        except FileNotFoundError:
            pass

    def _base_slug_for(self, item: Item) -> str:
        """
        Get a readable slugified version of the title for this item (may not be unique).
        """
        title = item.abbrev_title(max_len=FILENAME_SLUG_MAX_LEN)
        slug = slugify(title, max_length=FILENAME_SLUG_MAX_LEN, separator="_")
        return slug

    def _new_filename_for(self, item: Item) -> Tuple[str, Optional[str]]:
        """
        Get a suitable filename for this item that is close to the slugified title yet also unique.
        Also return the old filename if it's different.
        """
        slug = self._base_slug_for(item)

        # Get a unique name per item type.
        unique_slug, old_slugs = self.uniquifier.uniquify_historic(slug, item.get_full_suffix())

        type = item.type.value
        ext = item.get_file_ext().value

        # Suffix files with both item type and a suitable file extension.
        new_unique_filename = f"{unique_slug}.{type}.{ext}"

        old_filename = f"{old_slugs[0]}.{type}.{ext}" if old_slugs else None

        return new_unique_filename, old_filename

    def find_path_for(self, item: Item) -> Tuple[StorePath, Optional[StorePath]]:
        """
        Return the store path for an item. Store path may or may not already exist, depending on whether
        store_path is already set on the item or the an item with the same identity has been saved before.
        Returns `store_path, old_store_path` where `old_store_path` is the previous similarly named item
        (or None there is none).
        """
        item_id = item.item_id()
        old_filename = None
        if item.store_path:
            store_path = item.store_path
            return StorePath(str(store_path)), None
        elif item_id in self.id_map:
            # If this item has an identity and we've saved under that id before, use the same store path.
            store_path = self.id_map[item_id]
            log.message("Item with id %s already saved: %s", item_id, store_path)
            return StorePath(str(store_path)), None
        else:
            # We need to generate a new name.
            folder_path = Path(item_type_to_folder(item.type))
            filename, old_filename = self._new_filename_for(item)
            store_path = folder_path / filename

            old_store_path = None
            if old_filename and Path(self.base_dir / folder_path / old_filename).exists():
                old_store_path = StorePath(str(folder_path / old_filename))

            return StorePath(str(store_path)), old_store_path

    def save(self, item: Item) -> StorePath:
        """
        Save the item. Uses the store_path if it's already set or generates a new one.
        Updates item.store_path.
        """
        # If external file already exists within the workspace, the file is alrady saved (without metadata).
        if (
            item.external_path
            and path.exists(item.external_path)
            and path.commonpath([self.base_dir, item.external_path]) == str(self.base_dir)
        ):
            log.info("External file already saved: %s", item.external_path)
            store_path = StorePath(path.relpath(item.external_path, self.base_dir))
        else:
            # Otherwise it's still in memory or in a file outside the workspace and we need to save it.
            store_path, old_store_path = self.find_path_for(item)
            full_path = self.base_dir / store_path

            log.info("Saving item to %s: %s", full_path, item)

            # If we're overwriting an existing file, archive it first.
            if full_path.exists():
                try:
                    self.archive(store_path)
                except Exception as e:
                    log.error("Error archiving existing file: %s", e)

            # Now save the new item.
            try:
                if item.external_path:
                    copyfile_atomic(item.external_path, full_path)
                else:
                    if item.is_binary:
                        raise ValueError(f"Binary Items should be external files: {item}")

                    formatted_body = normalize_formatting(item.body_text(), item.format)

                    is_html = str(item.format) == str(Format.html)
                    fmf_write(
                        full_path,
                        formatted_body,
                        item.metadata(),
                        is_html=is_html,
                        key_sort=ITEM_FIELD_SORT,
                    )
            except IOError as e:
                log.error("Error saving item: %s", e)
                self.unarchive(store_path)
                raise e

            # Set filesystem file creation and modification times as well.
            if item.created_at:
                created_time = item.created_at.timestamp()
                modified_time = item.modified_at.timestamp() if item.modified_at else created_time
                os.utime(full_path, (created_time, modified_time))

            # Check if it's an exact duplicate of the previous file, to reduce clutter.
            if old_store_path:
                old_item = self.load(old_store_path)
                if item.content_equals(old_item):
                    log.message(
                        "New item is identical to previous version, will keep old item: %s",
                        old_store_path,
                    )
                    os.unlink(full_path)
                    store_path = old_store_path

        item.store_path = store_path
        self._index_item(store_path)

        log.message("%s Saved item: %s", EMOJI_SUCCESS, store_path)
        return store_path

    def load(self, store_path: StorePath) -> Item:
        """
        Load item at the given path.
        """
        _name, item_type, file_ext = _parse_check_filename(store_path)
        if FileExt.is_text(file_ext):
            # This is a known text format or a YAML file, so we can read the whole thing.
            body, metadata = fmf_read(self.base_dir / store_path)
            if not metadata:
                raise ValueError(f"No metadata found in file: {store_path}")

            return Item.from_dict(metadata, body=body, store_path=store_path)
        else:
            # This is a PDF or other binary file, so we just return the metadata.
            format = _format_from_ext(file_ext)
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
            orig_url = Url(file_path_or_url)
            url = canonicalize_url(orig_url)
            if url != orig_url:
                log.message("Canonicalized URL: %s -> %s", orig_url, url)
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
                    f"Unknown extension for file: {file_path} (known types are {", ".join(FileExt.__members__.keys())})"
                )
            format = Format.guess_by_file_ext(file_ext)
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

    def _remove_references(self, store_paths: List[StorePath]):
        self.selection.remove_values(store_paths)
        for store_path in store_paths:
            self._unindex_item(store_path)
        # TODO: Update metadata of all relations that point to this path too.

    def _rename_items(self, replacements: List[Tuple[StorePath, StorePath]]):
        self.selection.replace_values(replacements)
        for store_path, new_store_path in replacements:
            self._unindex_item(store_path)
            self._index_item(new_store_path)
        # TODO: Update metadata of all relations that point to this path too.

    def archive(self, store_path: StorePath) -> StorePath:
        """
        Archive the item by moving it into the archive directory.
        """
        log.message("Archiving item: %s -> %s", store_path, Path(ARCHIVE_DIR) / store_path)
        archive_path = self.archive_dir / store_path
        move_file(self.base_dir / store_path, archive_path)
        self._remove_references([store_path])
        return StorePath(join(ARCHIVE_DIR, store_path))

    def unarchive(self, store_path: StorePath):
        """
        Unarchive the item by moving back out of the archive directory.
        Path may be with or without the archive dir prefix.
        """
        log.info("Unarchiving item: %s", store_path)
        if commonpath([ARCHIVE_DIR, store_path]) == ARCHIVE_DIR:
            store_path = StorePath(relpath(store_path, ARCHIVE_DIR))
        original_path = self.base_dir / store_path
        move_file(self.archive_dir / store_path, original_path)
        return StorePath(store_path)

    def set_selection(self, selection: list[StorePath]):
        self.selection.set(selection)

    def get_selection(self) -> list[StorePath]:
        try:
            return self.selection.read()
        except OSError:
            raise InvalidStoreState("No selection saved in workspace")

    def get_action_params(self) -> Dict[str, str]:
        try:
            return self.action_params.read()
        except OSError:
            return {}

    def set_action_params(self, action_params: dict):
        self.action_params.set(action_params)

    def unselect(self, unselect_paths: list[StorePath]):
        current_selection = self.get_selection()
        new_selection = [path for path in current_selection if path not in unselect_paths]
        self.set_selection(new_selection)
        return new_selection

    def log_store_info(self):
        log.message(
            "Using workspace: %s (%s items)",
            path.abspath(self.base_dir),
            len(self.uniquifier),
        )
        # TODO: Log more info like number of items by type.

    def walk_by_folder(
        self, store_path: Optional[StorePath] = None, show_hidden: bool = False
    ) -> Generator[Tuple[StorePath, List[str]], None, None]:
        """
        Yields all files in each folder as `(store_dirname, filenames)` for each directory in the store.
        """

        path = self.base_dir / store_path if store_path else self.base_dir

        if not path.exists():
            raise ValueError(f"Directory not found: {path}")

        # Special case of a single file.
        if path.is_file():
            yield StorePath(relpath(path.parent, self.base_dir)), [path.name]
            return

        # Walk the directory.
        for dirname, dirnames, filenames in os.walk(path):
            # TODO: Support other sorting options.
            dirnames.sort()
            filenames.sort()

            store_dirname = relpath(dirname, self.base_dir)

            if not show_hidden and skippable_file(store_dirname):
                continue

            filtered_filenames = []
            for filename in filenames:
                store_filename = relpath(filename, self.base_dir)
                if not show_hidden and skippable_file(store_filename):
                    continue
                filtered_filenames.append(filename)

            if len(filtered_filenames) > 0:
                yield StorePath(str(store_dirname)), filtered_filenames

    def walk_items(
        self, store_path: Optional[StorePath] = None, show_hidden: bool = False
    ) -> Generator[StorePath, None, None]:
        """
        Yields StorePaths of items in a folder or the entire store.
        """
        for store_dirname, filenames in self.walk_by_folder(store_path, show_hidden):
            for filename in filenames:
                yield StorePath(join(store_dirname, filename))

    def canonicalize(self, store_path: StorePath) -> StorePath:
        """
        Canonicalize an item to make sure its filename and contents are in current format.
        """
        log.info("Canonicalizing item: %s", store_path)

        item = self.load(store_path)
        self.archive(store_path)
        new_store_path = self.save(item)

        # TODO: Handle checking if filename should change (may want this if we alter the slugify rules, etc.)
        return new_store_path
