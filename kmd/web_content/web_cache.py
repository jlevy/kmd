import os
import time
from enum import Enum
from pathlib import Path
from typing import Optional

import requests

from strif import copyfile_atomic

from kmd.config.logger import get_logger
from kmd.errors import FileNotFound, InvalidInput
from kmd.model.file_formats_model import choose_file_ext
from kmd.text_formatting.text_formatting import fmt_path
from kmd.util.download_url import download_url, user_agent_headers
from kmd.util.log_calls import log_if_modifies
from kmd.util.url import is_file_url, normalize_url, parse_file_url, Url
from kmd.web_content.dir_store import DirStore


log = get_logger(__name__)

_normalize_url = log_if_modifies(level="info")(normalize_url)


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


DEFAULT_SUFFIX = ""


def _suffix_for(url_or_path: Url | Path) -> str:
    return f".{choose_file_ext(url_or_path)}"


class WebCache(DirStore):
    """
    Storage and caching of local copies of web or file contents of any kind.

    The WebCache is a DirStore with a fetching mechanism based on a fixed object expiration time.

    Fetch timestamp is modification time on file. Thread safe since file creation is atomic.

    Also works for local files via file:// URLs.

    Supports a backup/restore mechanism to/from an S3 bucket. Supply `backup_url` to use.
    """

    # TODO: We don't fully handle fragments/sections of larger pages. It'd be preferable to extract
    # the part of the page at the anchor/fragment, but for now we ignore fragments and fetch/use
    # the whole page.
    # TODO: Consider saving HTTP headers as well.

    ALWAYS: float = 0
    NEVER: float = -1

    def __init__(
        self,
        root: Path,
        default_expiration_sec: float = NEVER,
        mode: WebCacheMode = WebCacheMode.LIVE,
        backup_url: Optional[Url] = None,
    ) -> None:
        """
        Expiration is in seconds, and can be NEVER or ALWAYS.
        """
        super().__init__(root)
        self.default_expiration_sec = default_expiration_sec
        self.session = requests.Session()
        # In case we want to cache a few types of files in the future.
        self.folder = "originals"
        self.mode = mode
        self.backup_url = backup_url

        if backup_url and mode in (WebCacheMode.TEST, WebCacheMode.UPDATE):
            self._restore(backup_url)

    def _normalize(self, url_or_path: Url | Path) -> Url | Path:
        if isinstance(url_or_path, Path):
            return url_or_path
        else:
            return _normalize_url(url_or_path)

    def _fetch_or_copy(self, url_or_path: Url | Path) -> Path:
        """
        Fetch or copy the given URL or local file to the cache.
        """
        if self.mode == WebCacheMode.TEST:
            raise InvalidCacheState("_download called in test mode")

        key = self._normalize(url_or_path)
        cache_path = self.path_for(key, folder=self.folder, suffix=_suffix_for(url_or_path))

        if isinstance(url_or_path, Path) or is_file_url(url_or_path):
            if isinstance(url_or_path, Path):
                file_path = url_or_path
            else:
                file_path = parse_file_url(url_or_path)
                if not file_path:
                    raise InvalidInput(f"Not a file URL: {url_or_path}")
            if not file_path.exists():
                raise FileNotFound(f"File not found: {file_path}")
            log.message(
                "Copying local file to cache: %s -> %s", fmt_path(file_path), fmt_path(cache_path)
            )
            copyfile_atomic(file_path, cache_path, make_parents=True)
        else:
            url = _normalize_url(url_or_path)
            log.info("Downloading to cache: %s -> %s", url, fmt_path(cache_path))
            download_url(
                url, cache_path, silent=True, timeout=TIMEOUT, headers=user_agent_headers()
            )

        return cache_path

    def _age_in_sec(self, cache_path: Path) -> float:
        now = time.time()
        return now - read_mtime(cache_path)

    def _is_expired(self, cache_path: Path, expiration_sec: Optional[float] = None) -> bool:
        if self.mode in (WebCacheMode.TEST, WebCacheMode.UPDATE):
            return False

        if expiration_sec is None:
            expiration_sec = self.default_expiration_sec

        if expiration_sec == self.ALWAYS:
            return True
        elif expiration_sec == self.NEVER:
            return False

        return self._age_in_sec(cache_path) > expiration_sec

    def is_cached(self, url_or_path: Url | Path, expiration_sec: Optional[float] = None) -> bool:
        if expiration_sec is None:
            expiration_sec = self.default_expiration_sec

        cache_path = self.find(url_or_path, folder=self.folder, suffix=_suffix_for(url_or_path))

        return cache_path is not None and not self._is_expired(cache_path, expiration_sec)

    def cache(
        self, url_or_path: Url | Path, expiration_sec: Optional[float] = None
    ) -> tuple[Path, bool]:
        """
        Returns cached download path of given URL and whether it was previously cached.
        For file:// URLs does a copy.
        """
        key = self._normalize(url_or_path)
        cache_path = self.find(key, folder=self.folder, suffix=_suffix_for(url_or_path))

        if cache_path and not self._is_expired(cache_path, expiration_sec):
            log.info("URL in cache, not fetching: %s: %s", key, fmt_path(cache_path))
            return cache_path, True
        else:
            log.info("Caching new copy: %s", key)
            return (
                self._fetch_or_copy(key),
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
