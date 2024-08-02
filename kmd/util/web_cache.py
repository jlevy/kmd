"""
Storage and caching of downloaded and processed web pages.
"""

from pathlib import Path
from typing import Callable, Optional
import os
from os import path
import time
from enum import Enum
import requests
import strif
from strif import clean_alphanum_hash
from kmd.util.download_url import download_url, user_agent_headers
from kmd.util.url import Url, normalize_url
from kmd.config.logger import get_logger

log = get_logger(__name__)


def aws_cli(*cmd):
    # Import dynamically to avoid hard dependency.
    from awscli.clidriver import create_clidriver  # type: ignore

    log.info("awscli: aws %s" % " ".join(cmd))
    # Run awscli in the same process
    exit_code = create_clidriver().main(cmd)

    # Deal with problems
    if exit_code > 0:
        raise RuntimeError("AWS CLI exited with code {}".format(exit_code))


def default_hash_func(key):
    return clean_alphanum_hash(key, max_length=80)


class DirStore:
    """
    A simple file storage scheme: A directory of items, organized into folders, stored by readable
    but uniquely hashed keys so it's possible to inspect the directory.
    """

    # TODO: Would be useful to support optional additional root directories, with write always
    # being to the main root but cache lookups checking in sequence, allowing a hierarchy of caches.

    def __init__(self, root: Path, hash_func: Optional[Callable[[str], str]] = None) -> None:
        self.root: Path = root
        self.hash_func: Callable[[str], str] = hash_func or default_hash_func
        strif.make_all_dirs(root)

    def path_for(
        self, key: str, folder: Optional[str] = None, suffix: Optional[str] = None
    ) -> Path:
        """A unique file path with the given key.

        It's up to the client how to use it.
        """
        full_path = self.hash_func(key)
        if suffix:
            full_path += suffix
        if folder:
            full_path = path.join(folder, full_path)
        full_path = self.root / full_path

        return full_path

    def find(
        self, key: str, folder: Optional[str] = None, suffix: Optional[str] = None
    ) -> Optional[Path]:
        local_path = self.path_for(key, folder, suffix)
        return local_path if path.exists(local_path) else None

    def find_all(
        self, keys: list[str], folder: Optional[str] = None, suffix: Optional[str] = None
    ) -> dict[str, Optional[Path]]:
        """
        Look up all existing cached results for the set of keys. This should work fine but could
        be optimized for large batches.
        """
        return {key: self.find(key, folder=folder, suffix=suffix) for key in keys}

    def _restore(self, url: Url, folder: str = "") -> None:
        # We *don't* add '--delete' arg to delete remote files based on local status.
        aws_cli("s3", "sync", path.join(url, folder), self.root / folder)

    def _backup(self, url: Url, folder: str = "") -> None:
        # We *don't* add '--delete' arg to delete local files based on remote status.
        aws_cli("s3", "sync", self.root / folder, path.join(url, folder))

    # TODO: Consider other methods to purge or sync with --delete.


def read_mtime(path):
    """
    Modification time for a file, or 0 if file doesn't exist or is not readable.
    """
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0
    return mtime


TIMEOUT = 30


class WebCacheMode(Enum):
    LIVE = 1
    TEST = 2
    UPDATE = 3


class InvalidCacheState(RuntimeError):
    pass


class WebCache(DirStore):
    """
    The web cache is a DirStore with a fetching mechanism based on a fixed object expiration time.

    Fetch timestamp is modification time on file. Thread safe since file creation is atomic.

    Also supports a backup/restore mechanism to/from an S3 bucket. Supply `backup_url` to use.
    """

    # TODO: We don't fully handle fragments/sections of larger pages. It'd be preferable to extract
    # the part of the page at the anchor/fragment, but for now we ignore fragments and fetch/use
    # the whole page.

    ALWAYS: float = 0
    NEVER: float = -1

    # TODO: Save status codes and HTTP headers as well.

    def __init__(
        self,
        root: Path,
        default_expiration_sec: float = NEVER,
        folder: str = "raw",
        suffix: str = ".page",
        mode: WebCacheMode = WebCacheMode.LIVE,
        backup_url: Optional[Url] = None,
        verbose: bool = False,
    ) -> None:
        """Expiration is in seconds, and can be NEVER or ALWAYS."""
        super().__init__(root)
        self.default_expiration_sec = default_expiration_sec
        self.session = requests.Session()
        self.folder = folder
        self.suffix = suffix
        self.mode = mode
        self.backup_url = backup_url
        self.verbose = verbose

        if backup_url and mode in (WebCacheMode.TEST, WebCacheMode.UPDATE):
            self._restore(backup_url, self.folder)

    def find_url(
        self, url: Url, folder: Optional[str] = None, suffix: Optional[str] = None
    ) -> Optional[Path]:
        url = normalize_url(url)
        return self.find(url, folder=folder or self.folder, suffix=suffix or self.suffix)

    def _download(self, url: Url) -> Path:
        if self.mode == WebCacheMode.TEST:
            raise InvalidCacheState("_download called in test mode")

        url = normalize_url(url)
        local_path = self.path_for(url, folder=self.folder, suffix=self.suffix)
        download_url(url, local_path, silent=True, timeout=TIMEOUT, headers=user_agent_headers())
        return local_path

    def _age_in_sec(self, local_path: Path) -> float:
        now = time.time()
        return now - read_mtime(local_path)

    def _is_expired(self, local_path: Path, expiration_sec: Optional[float] = None) -> bool:
        if self.mode in (WebCacheMode.TEST, WebCacheMode.UPDATE):
            return False

        if expiration_sec is None:
            expiration_sec = self.default_expiration_sec

        if expiration_sec == self.ALWAYS:
            return True
        elif expiration_sec == self.NEVER:
            return False

        return self._age_in_sec(local_path) > expiration_sec

    def is_cached(self, url: Url, expiration_sec: Optional[float] = None) -> bool:
        if expiration_sec is None:
            expiration_sec = self.default_expiration_sec

        local_path = self.find(url, folder=self.folder, suffix=self.suffix)
        return local_path is not None and not self._is_expired(local_path, expiration_sec)

    def fetch(self, url: Url, expiration_sec: Optional[float] = None) -> tuple[Path, bool]:
        """
        Returns cached download path of given URL and whether it was previously cached.
        """
        url = normalize_url(url)
        local_path = self.find(url, folder=self.folder, suffix=self.suffix)
        if local_path and not self._is_expired(local_path, expiration_sec):
            log.info("URL in cache, not fetching: %s: %s", url, local_path)
            return local_path, True
        else:
            if self.verbose:
                log.info("fetching: %s", url)
            return (
                self._download(url),
                False,
            )

    def backup(self) -> None:
        if not self.backup_url:
            raise InvalidCacheState("Backup called without backup_url")
        self._backup(self.backup_url, self.folder)

    def backup_all(self) -> None:
        if not self.backup_url:
            raise InvalidCacheState("Backup called without backup_url")
        self._backup(self.backup_url, "")

    def restore(self) -> None:
        if not self.backup_url:
            raise InvalidCacheState("Restore called without backup_url")
        self._restore(self.backup_url, self.folder)

    def restore_all(self) -> None:
        if not self.backup_url:
            raise InvalidCacheState("Restore called without backup_url")
        self._restore(self.backup_url, "")
