import functools
import os
import threading
import time
from os import path
from os.path import join, relpath
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, TypeVar

from kmd.config.logger import get_logger, log_file_path
from kmd.config.text_styles import EMOJI_SAVED

from kmd.errors import FileExists, FileNotFound, InvalidFilename, SkippableError
from kmd.file_storage.item_file_format import read_item, write_item
from kmd.file_storage.metadata_dirs import MetadataDirs
from kmd.file_storage.store_filenames import folder_for_type, join_suffix, parse_item_filename
from kmd.file_tools.file_walk import IgnoreFilter, walk_by_dir
from kmd.model.args_model import fmt_loc, Locator
from kmd.model.canon_url import canonicalize_url
from kmd.model.file_formats_model import Format, is_ignored
from kmd.model.items_model import Item, ItemId, ItemType
from kmd.model.paths_model import StorePath
from kmd.query.vector_index import WsVectorIndex
from kmd.shell.shell_output import cprint
from kmd.util.format_utils import fmt_lines
from kmd.util.log_calls import format_duration, log_calls

from kmd.util.strif import copyfile_atomic, hash_file, move_file
from kmd.util.uniquifier import Uniquifier
from kmd.util.url import is_url, Url
from kmd.workspaces.param_state import ParamState
from kmd.workspaces.selections import SelectionHistory
from kmd.workspaces.workspace_names import workspace_name

log = get_logger(__name__)


T = TypeVar("T")


def synchronized(method: Callable[..., T]) -> Callable[..., T]:
    """
    Simple way to synchronize a few methods.
    """

    @functools.wraps(method)
    def synchronized_method(self, *args: Any, **kwargs: Any) -> T:
        with self._lock:
            return method(self, *args, **kwargs)

    return synchronized_method


class FileStore:
    """
    The main class to manage files in a workspace, holding settings and files with items.
    Should be thread safe since file operations are atomic and mutable state is synchronized.
    """

    # TODO: Consider using a pluggable filesystem (fsspec AbstractFileSystem).

    def __init__(self, base_dir: Path, is_sandbox: bool):
        self.base_dir = base_dir.resolve()
        self.name = workspace_name(self.base_dir)
        self.is_sandbox = is_sandbox
        self._lock = threading.RLock()
        self.reload()

    @synchronized
    def reload(self):
        """
        Load or reload all state.
        """
        self.start_time = time.time()
        self.info_logged = False
        self.warnings: List[str] = []

        # TODO: Move this to its own IdentifierIndex class, and make it exactly mirror disk state.
        self.uniquifier = Uniquifier()
        self.id_map: Dict[ItemId, StorePath] = {}

        self._id_index_init()

        self.dirs = MetadataDirs(self.base_dir)
        self.dirs.initialize()

        self.vector_index = WsVectorIndex(self.base_dir / self.dirs.index_dir)

        # Initialize selection with history support
        self.selections = SelectionHistory.init(self.base_dir / self.dirs.selection_yml)

        # Filter out any non-existent paths from the initial selection
        if self.selections.history:
            self._filter_selection_paths()

        self.params = ParamState(self.base_dir / self.dirs.params_yml)

        self.end_time = time.time()

        # Warm the item cache in a separate thread.
        from kmd.file_storage.file_cache_warmer import warm_file_store

        warm_file_store(self)

    def __str__(self):
        return f"FileStore(~{self.name})"

    def _id_index_init(self):
        num_dups = 0
        for root, dirnames, filenames in os.walk(self.base_dir):
            dirnames[:] = [d for d in dirnames if not is_ignored(d)]
            for filename in filenames:
                if not is_ignored(filename):
                    store_path = StorePath(path.relpath(join(root, filename), self.base_dir))
                    dup_path = self._id_index_item(store_path)
                    if dup_path:
                        num_dups += 1

        if num_dups > 0:
            self.warnings.append(
                f"Found {num_dups} duplicate items in store. See `logs` for details."
            )

    @synchronized
    def _id_index_item(self, store_path: StorePath) -> Optional[StorePath]:
        """
        Update metadata index with a new item.
        """
        name, item_type, _format, file_ext = parse_item_filename(store_path)
        if not file_ext:
            log.debug("Skipping file with unrecognized name or extension: %s", fmt_loc(store_path))
            return None

        full_suffix = join_suffix(item_type.name, file_ext.name) if item_type else file_ext.name
        self.uniquifier.add(name, full_suffix)

        dup_path = None

        try:
            item = self.load(store_path)
            item_id = item.item_id()
            if item_id:
                old_path = self.id_map.get(item_id)
                if old_path and old_path != store_path:
                    dup_path = old_path
                    log.info(
                        "Duplicate items (%s):\n%s", item_id, fmt_lines([old_path, store_path])
                    )
                self.id_map[item_id] = store_path
        except SkippableError as e:
            log.warning("Could not read file, skipping: %s: %s", fmt_loc(store_path), e)

        return dup_path

    @synchronized
    def _id_unindex_item(self, store_path: StorePath):
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
        except (FileNotFoundError, InvalidFilename):
            pass

    @synchronized
    def _new_filename_for(self, item: Item) -> Tuple[str, Optional[str]]:
        """
        Get a suitable filename for this item that is close to the slugified title yet also unique.
        Also return the old filename if it's different.
        """
        slug = item.title_slug()
        full_suffix = item.get_full_suffix()
        # Get a unique name per item type.
        unique_slug, old_slugs = self.uniquifier.uniquify_historic(slug, full_suffix)

        # Suffix files with both item type and a suitable file extension.
        new_unique_filename = join_suffix(unique_slug, full_suffix)

        old_filename = join_suffix(old_slugs[0], full_suffix) if old_slugs else None

        return new_unique_filename, old_filename

    def _default_path_for(self, item: Item) -> StorePath:
        folder_path = folder_for_type(item.type)
        slug = item.title_slug()
        suffix = item.get_full_suffix()
        return StorePath(folder_path / join_suffix(slug, suffix))

    def exists(self, store_path: StorePath) -> bool:
        return (self.base_dir / store_path).exists()

    def resolve_path(self, path: Path | StorePath) -> Optional[StorePath]:
        """
        Return a StorePath if the given path is within the store, otherwise None.
        If it is already a StorePath, return it unchanged.
        """
        if isinstance(path, StorePath):
            return path
        resolved = path.resolve()
        if resolved.is_relative_to(self.base_dir):
            return StorePath(resolved.relative_to(self.base_dir))
        else:
            return None

    @synchronized
    def find_by_id(self, item: Item) -> Optional[StorePath]:
        """
        Best effort to see if an item with the same identity is already in the store.
        """
        item_id = item.item_id()
        log.info("Looking for item by id: %s", item_id)
        if not item_id:
            return None
        else:
            store_path = self.id_map.get(item_id)
            if not store_path:
                # Just in case the id_map is not complete, check the default path too.
                default_path = self._default_path_for(item)
                if self.exists(default_path):
                    old_item = self.load(default_path)
                    if old_item.item_id() == item_id:
                        log.message(
                            "Item with the same id already saved (disk check):\n%s",
                            fmt_lines([fmt_loc(default_path), item_id]),
                        )
                        store_path = default_path
                        self.id_map[item_id] = default_path
                        return default_path
            if store_path and self.exists(store_path):
                log.message(
                    "Item with the same id already saved (disk check):\n%s",
                    fmt_lines([fmt_loc(store_path), item_id]),
                )
                return store_path
        return None

    @synchronized
    def store_path_for(
        self, item: Item, as_tmp: bool = False
    ) -> Tuple[StorePath, bool, Optional[StorePath]]:
        """
        Return the store path for an item. If the item already has a `store_path`, we use that.
        Otherwise we need to find the store path or generate a new one.

        Returns `store_path, found, old_store_path` where `found` indicates whether the path was
        already found (in the item or in the store by checking for identity) and `old_store_path`
        is the previous similarly named item with a different identity (or None there is none).
        """
        item_id = item.item_id()
        old_filename = None
        if as_tmp:
            return self._tmp_path_for(item), False, None
        elif item.store_path:
            return StorePath(item.store_path), True, None
        elif item_id in self.id_map:
            # If this item has an identity and we've saved under that id before, use the same store path.
            store_path = self.id_map[item_id]
            log.info(
                "Found existing item with same id:\n%s",
                fmt_lines([fmt_loc(store_path), item_id]),
            )
            return store_path, True, None
        else:
            # We need to generate a new filename.
            folder_path = folder_for_type(item.type)
            filename, old_filename = self._new_filename_for(item)
            store_path = folder_path / filename

            old_store_path = None
            if old_filename and Path(self.base_dir / folder_path / old_filename).exists():
                old_store_path = StorePath(folder_path / old_filename)

            return StorePath(store_path), False, old_store_path

    def _tmp_path_for(self, item: Item) -> StorePath:
        """
        Find a path for an item in the tmp directory.
        """
        if not item.store_path:
            store_path, _found, _old = self.store_path_for(item, as_tmp=False)
            return StorePath(self.dirs.tmp_dir / store_path)
        elif (self.base_dir / item.store_path).is_relative_to(self.dirs.tmp_dir):
            return StorePath(item.store_path)
        else:
            return StorePath(self.dirs.tmp_dir / item.store_path)

    @log_calls()
    def save(self, item: Item, as_tmp: bool = False, overwrite: bool = True) -> StorePath:
        """
        Save the item. Uses the store_path if it's already set or generates a new one.
        Updates item.store_path.
        """
        # If external file already exists within the workspace, the file is already saved (without metadata).
        if item.external_path and Path(item.external_path).resolve().is_relative_to(self.base_dir):
            log.message("External file already saved: %s", fmt_loc(item.external_path))
            rel_path = Path(item.external_path).relative_to(self.base_dir)
            # Indicate this is really an item with a store path, not an external path.
            item.store_path = str(rel_path)
            item.external_path = None
            return StorePath(rel_path)
        else:
            # Otherwise it's still in memory or in a file outside the workspace and we need to save it.
            store_path, found, old_store_path = self.store_path_for(item, as_tmp=as_tmp)

            if not overwrite and found:
                log.message("Skipping save of item already saved: %s", fmt_loc(store_path))
                item.store_path = str(store_path)
                return store_path

            full_path = self.base_dir / store_path

            log.info("Saving item to %s: %s", fmt_loc(full_path), item)

            # If we're overwriting an existing file, archive it first.
            if full_path.exists():
                try:
                    self.archive(store_path, quiet=True)
                except Exception as e:
                    log.info("Exception archiving existing file: %s", e)

            # Now save the new item.
            try:
                if item.external_path:
                    copyfile_atomic(item.external_path, full_path)
                else:
                    write_item(item, full_path)
            except IOError as e:
                log.error("Error saving item: %s", e)
                try:
                    self.unarchive(store_path)
                except Exception:
                    pass
                raise e

            # Set filesystem file creation and modification times as well.
            if item.created_at:
                created_time = item.created_at.timestamp()
                modified_time = item.modified_at.timestamp() if item.modified_at else created_time
                os.utime(full_path, (modified_time, modified_time))

            # Check if it's an exact duplicate of the previous file, to reduce clutter.
            if old_store_path:
                old_item = self.load(old_store_path)
                new_item = self.load(store_path)  # Reload it to get normalized text.
                if new_item.content_equals(old_item):
                    log.message(
                        "New item is identical to previous version, will keep old item: %s",
                        old_store_path,
                    )
                    os.unlink(full_path)
                    store_path = old_store_path

        # Update in-memory store_path only after successful save.
        item.store_path = str(store_path)
        self._id_index_item(store_path)

        log.message("%s Saved item:\n%s", EMOJI_SAVED, fmt_lines([fmt_loc(store_path)]))
        return store_path

    @log_calls(level="debug")
    def load(self, store_path: StorePath) -> Item:
        """
        Load item at the given path.
        """
        return read_item(self.base_dir / store_path, self.base_dir)

    def hash(self, store_path: StorePath) -> str:
        """
        Get a hash of the item at the given path.
        """
        return hash_file(self.base_dir / store_path, algorithm="sha1").with_prefix

    def import_item(
        self, locator: Locator, as_type: ItemType = ItemType.resource, reimport: bool = False
    ) -> StorePath:
        """
        Add resources from a files or URLs. If a locator is a string or Path, copy it into
        the store. If it's already there, just return the store path.
        """
        if is_url(str(locator)):
            # Import a URL as a resource.
            orig_url = Url(str(locator))
            url = canonicalize_url(orig_url)
            if url != orig_url:
                log.message("Canonicalized URL: %s -> %s", orig_url, url)
            item = Item(as_type, url=url, format=Format.url)
            store_path = self.save(item)
            return store_path
        elif isinstance(locator, StorePath) and not reimport:
            # TODO: Maybe check if we need to insert metadata, in case it's a regular file just
            # sitting in the store.
            log.info("Store path already imported: %s", fmt_loc(locator))
            return locator
        else:
            # We have a path, possibly outside of or inside of the store.
            path = Path(locator).resolve()
            if path.is_relative_to(self.base_dir):
                store_path = StorePath(path.relative_to(self.base_dir))
                if self.exists(store_path) and not reimport:
                    log.message("Path already imported: %s", fmt_loc(store_path))
                    return store_path

            if not path.exists():
                raise FileNotFound(f"File not found: {fmt_loc(path)}")

            # It's a path outside the store, so copy it in.
            _name, filename_item_type, format, _file_ext = parse_item_filename(path)

            if filename_item_type:
                as_type = filename_item_type
            if format and format.supports_frontmatter:
                log.message("Importing text file: %s", fmt_loc(path))
                # This will read the file with or without frontmatter.
                # We are importing so we want to drop the external path so we save the body.
                item = read_item(path, self.base_dir)
                item.external_path = None

                if item.type != as_type:
                    log.warning(
                        "Reimporting as item type `%s` instead of `%s`: %s",
                        as_type.value,
                        item.type.value,
                        fmt_loc(path),
                    )
                    item.type = as_type

                # This will only have a store path if it was already in the store; otherwise
                # we'll pick a new store path.
                store_path = self.save(item)
                log.info("Imported text file: %s", item.as_str())
            else:
                log.message("Importing non-text file: %s", fmt_loc(path))
                # Binary or other files we just copy over as-is, preserving the name.
                # We know the extension is recognized.
                item = Item.from_external_path(path)
                store_path, _found, _prev = self.store_path_for(item)
                if self.exists(store_path):
                    raise FileExists(f"Resource already in store: {fmt_loc(store_path)}")

                if item.type != as_type:
                    log.warning(
                        "Reimporting as item type `%s` instead of `%s`: %s",
                        as_type.value,
                        item.type.value,
                        fmt_loc(path),
                    )
                    item.type = as_type

                log.message("Importing resource: %s -> %s", fmt_loc(path), fmt_loc(store_path))
                copyfile_atomic(path, self.base_dir / store_path, make_parents=True)
            return store_path

    def import_items(
        self, *locators: Locator, as_type: ItemType = ItemType.resource, reimport: bool = False
    ) -> List[StorePath]:
        return [self.import_item(locator, as_type, reimport) for locator in locators]

    def _filter_selection_paths(self):
        """
        Filter out any paths that don't exist from all selections.
        """
        non_existent = set()
        for i, selection in enumerate(reversed(self.selections.history)):
            non_existent.update(p for p in selection.paths if not self.exists(p))

        if non_existent:
            log.warning(
                "Filtering out %s non-existent paths from selection history (%s selections, %s paths).",
                len(non_existent),
                len(self.selections.history),
                len(non_existent),
            )
        self.selections.remove_values(non_existent)

    @synchronized
    def _remove_references(self, store_paths: List[StorePath]):
        """
        Remove references to store_paths from selections and id index.
        """
        self.selections.remove_values(store_paths)
        for store_path in store_paths:
            self._id_unindex_item(store_path)
        # TODO: Update metadata of all relations that point to this path too.

    @synchronized
    def _rename_items(self, replacements: List[Tuple[StorePath, StorePath]]):
        """
        Update references when items are renamed.
        """
        self.selections.replace_values(replacements)
        for store_path, new_store_path in replacements:
            self._id_unindex_item(store_path)
            self._id_index_item(new_store_path)
        # TODO: Update metadata of all relations that point to this path too.

    def archive(
        self, store_path: StorePath, missing_ok: bool = False, quiet: bool = False
    ) -> StorePath:
        """
        Archive the item by moving it into the archive directory.
        """
        if not quiet:
            log.message(
                "Archiving item: %s -> %s/",
                fmt_loc(store_path),
                fmt_loc(self.dirs.archive_dir),
            )
        orig_path = self.base_dir / store_path
        archive_path = self.dirs.archive_dir / store_path
        if missing_ok and not orig_path.exists():
            log.message("Item to archive not found so moving on: %s", fmt_loc(orig_path))
            return store_path
        move_file(orig_path, archive_path)
        self._remove_references([store_path])

        archive_path = StorePath(self.dirs.archive_dir / store_path)
        return archive_path

    def unarchive(self, store_path: StorePath) -> StorePath:
        """
        Unarchive the item by moving back out of the archive directory.
        Path may be with or without the archive dir prefix.
        """
        full_input_path = (self.base_dir / store_path).resolve()
        full_archive_path = (self.base_dir / self.dirs.archive_dir).resolve()
        if full_input_path.is_relative_to(full_archive_path):
            store_path = StorePath(relpath(full_input_path, full_archive_path))
        original_path = self.base_dir / store_path
        move_file(full_input_path, original_path)
        return StorePath(store_path)

    def log_store_info(self, once: bool = False):
        if once and self.info_logged:
            return
        self.info_logged = True

        cprint()
        log.message(
            "Using workspace: %s (%s items)",
            path.abspath(self.base_dir),
            len(self.uniquifier),
        )
        log.message("Logging to: %s", fmt_loc(log_file_path().absolute()))
        log.message("Media cache: %s", fmt_loc(self.base_dir / self.dirs.media_cache_dir))
        log.message("Content cache: %s", fmt_loc(self.base_dir / self.dirs.content_cache_dir))
        for warning in self.warnings:
            log.warning("%s", warning)

        if self.is_sandbox:
            log.warning("Note you are using the default sandbox workspace.")
            log.warning("Create or switch to a workspace with the `workspace` command.")

        log.info("File store startup took %s.", format_duration(self.end_time - self.start_time))
        # TODO: Log more info like number of items by type.

    def walk_items(
        self,
        store_path: Optional[StorePath] = None,
        ignore: Optional[IgnoreFilter] = is_ignored,
    ) -> Generator[StorePath, None, None]:
        """
        Yields StorePaths of items in a folder or the entire store.
        """
        start_path = self.base_dir / store_path if store_path else self.base_dir
        for flist in walk_by_dir(start_path, relative_to=self.base_dir, ignore=ignore):
            store_dirname = flist.parent_dir
            for filename in flist.filenames:
                yield StorePath(join(store_dirname, filename))

    def normalize(self, store_path: StorePath) -> StorePath:
        """
        Normalize an item or all items in a folder to make sure contents are in current
        format.
        """
        log.info("Normalizing item: %s", fmt_loc(store_path))

        item = self.load(store_path)
        new_store_path = self.save(item)

        return new_store_path
