import copy
import threading
from pathlib import Path
from typing import Generic, Optional, Tuple, TypeVar

from cachetools import LRUCache

from kmd.web_content.dir_store import file_mtime_hash

T = TypeVar("T")


class FileMtimeCache(Generic[T]):
    """
    A simple in-memory cache that stores loaded values from files.
    """

    def __init__(self, max_size):
        self.cache: LRUCache[str, Tuple[str, T]] = LRUCache(maxsize=max_size)
        self.lock = threading.Lock()

    def _cache_key(self, path: Path) -> str:
        return str(path.resolve())

    def read(self, path: Path) -> Optional[T]:
        """
        Returns the cached item (actually a deep copy to be safe) if the item is present
        and the file hasn't changed; otherwise, returns None.
        """
        key = self._cache_key(path)
        mtime_hash = file_mtime_hash(path)
        with self.lock:
            cache_entry = self.cache.get(key)
            if cache_entry:
                cached_mtime_hash, cached_value = cache_entry
                if cached_mtime_hash == mtime_hash:
                    return copy.deepcopy(cached_value)
                else:
                    # Cache is outdated
                    del self.cache[key]
        return None

    def update(self, path: Path, value: T) -> None:
        """
        Updates the cache with the new value for the given path.
        """
        key = self._cache_key(path)
        mtime_hash = file_mtime_hash(path)
        with self.lock:
            self.cache[key] = (mtime_hash, value)

    def delete(self, path: Path) -> None:
        """
        Removes the cached value for the given path.
        """
        key = self._cache_key(path)
        with self.lock:
            if key in self.cache:
                del self.cache[key]
