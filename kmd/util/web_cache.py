"""
Storage and caching of downloaded and processed web pages.
"""

import logging
import os
from os import path
import time
from enum import Enum
from urllib.parse import urlsplit, urlunsplit
import requests
import strif
from .download_url import download_url, user_agent_headers
from .identifier_utils import clean_alphanum_hash

log = logging.getLogger(__name__)


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

    def __init__(self, root, hash_func=None):
        self.root = root
        self.hash_func = hash_func or default_hash_func
        strif.make_all_dirs(root)

    def path_for(self, key, folder=None, suffix=None):
        """A unique file path with the given key.

        It's up to the client how to use it.
        """
        full_path = self.hash_func(key)
        if suffix:
            full_path += suffix
        if folder:
            full_path = path.join(folder, full_path)
        full_path = path.join(self.root, full_path)

        return full_path

    def find(self, key, folder=None, suffix=None):
        local_path = self.path_for(key, folder, suffix)
        return local_path if path.exists(local_path) else None

    def find_all(self, keys, folder=None, suffix=None):
        """Look up all existing cached results for the set of keys.

        This should work fine but could be optimized for large batches.
        """
        return {key: self.find(key, folder=folder, suffix=suffix) for key in keys}

    def _restore(self, url, folder=""):
        # We *don't* add '--delete' arg to delete remote files based on local status.
        aws_cli("s3", "sync", path.join(url, folder), path.join(self.root, folder))

    def _backup(self, url, folder=""):
        # We *don't* add '--delete' arg to delete local files based on remote status.
        aws_cli("s3", "sync", path.join(self.root, folder), path.join(url, folder))

    # TODO: Consider other methods to purge or sync with --delete.


def read_mtime(path):
    """
    Modification time for a file, or 0 if file doesn't exist or is not readable.
    """
    try:
        mtime = os.path.getmtime(path)
    except:
        mtime = 0
    return mtime


TIMEOUT = 30


def normalize_url(url):
    """
    Minimal URL normalization. Mainly to deal with fragments/sections of
    larger pages.

    TODO: It'd be preferable to remove this step and actually extract the part of the page at the anchor/fragment,
    but for now we fetch/use the whole page.
    """
    scheme, netloc, path, query, fragment = urlsplit(url)
    normalized_url = urlunsplit((scheme, netloc, path, query, None))
    if url != normalized_url:
        log.info("Normalized URL: %s -> %s" % (url, normalized_url))
    return normalized_url


class WebCacheMode(Enum):
    LIVE = 1
    TEST = 2
    UPDATE = 3


class TestingModeException(Exception):
    pass


class WebCache(DirStore):
    """
    The web cache is a DirStore with a fetching mechanism based on a fixed object expiration time.

    Fetch timestamp is modification time on file. Thread safe since file creation is atomic.
    """

    ALWAYS = 0
    NEVER = -1

    # TODO: Save status codes and HTTP headers as well.

    def __init__(
        self,
        root,
        default_expiration=NEVER,
        folder="raw",
        suffix=".page",
        mode=WebCacheMode.LIVE,
        url=None,
        verbose=False,
    ):
        """Expiration is in seconds, and can be NEVER or ALWAYS."""
        super().__init__(root)
        self.default_expiration = default_expiration
        self.session = requests.Session()
        self.folder = folder
        self.suffix = suffix
        self.mode = mode
        self.url = url
        self.verbose = verbose

        if url and mode in (WebCacheMode.TEST, WebCacheMode.UPDATE):
            self._restore(url, self.folder)

    def find_url(self, url, folder=None, suffix=None):
        url = normalize_url(url)
        return self.find(url, folder=folder or self.folder, suffix=suffix or self.suffix)

    def _download(self, url):
        if self.mode == WebCacheMode.TEST:
            raise TestingModeException("_download called in test mode")

        url = normalize_url(url)
        local_path = self.path_for(url, folder=self.folder, suffix=self.suffix)
        download_url(url, local_path, silent=True, timeout=TIMEOUT, headers=user_agent_headers())
        return local_path

    def _age(self, local_path):
        now = time.time()
        return now - read_mtime(local_path)

    def _is_expired(self, local_path, expiration=None):
        if self.mode in (WebCacheMode.TEST, WebCacheMode.UPDATE):
            return False

        if expiration is None:
            expiration = self.default_expiration

        if expiration == self.ALWAYS:
            return True
        elif expiration == self.NEVER:
            return False

        return self._age(local_path) > expiration

    def is_cached(self, url, expiration=None):
        if expiration is None:
            expiration = self.default_expiration

        local_path = self.find(url, folder=self.folder, suffix=self.suffix)
        return local_path and not self._is_expired(local_path, expiration)

    def fetch(self, url, expiration=None):
        """Returns cached download path of given URL and whether it was
        previously cached."""
        url = normalize_url(url)
        local_path = self.find(url, folder=self.folder, suffix=self.suffix)
        if local_path and not self._is_expired(local_path, expiration):
            return True, local_path
        else:
            if self.verbose:
                log.info("fetching: %s", url)
            return False, self._download(url)

    def backup(self):
        self._backup(self.url, self.folder)

    def backup_all(self):
        self._backup(self.url, "")

    def restore(self):
        self._restore(self.url, self.folder)

    def restore_all(self):
        self._restore(self.url, "")
