import os
from os import path
from pathlib import Path
from typing import Callable, Dict, List, Optional

from kmd.config.logger import get_logger
from kmd.util.strif import clean_alphanum_hash
from kmd.util.url import Url


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


def file_mtime_hash(path: Path) -> str:
    name = path.name
    size = path.stat().st_size
    mtime = path.stat().st_mtime_ns  # Nanosecond precision works on most platforms.
    key = f"{name}-{size}-{mtime}"
    return clean_alphanum_hash(key, max_length=80, max_hash_len=10)


def string_hash(key: str) -> str:
    return clean_alphanum_hash(key, max_length=80)


HashFunc = Callable[[str | Path], str]


def default_hash_func(key: str | Path) -> str:
    if isinstance(key, Path):
        return file_mtime_hash(key)
    elif isinstance(key, str):
        return string_hash(key)
    else:
        raise ValueError(f"Invalid key type: {type(key)}")


class DirStore:
    """
    A simple file storage scheme: A directory of items, organized into folders, stored by readable
    but uniquely hashed keys so it's possible to inspect the directory.
    """

    # TODO: Would be useful to support optional additional root directories, with write always
    # being to the main root but cache lookups checking in sequence, allowing a hierarchy of caches.

    def __init__(self, root: Path, hash_func: Optional[HashFunc] = None) -> None:
        self.root: Path = root
        self.hash_func: HashFunc = hash_func or default_hash_func
        os.makedirs(self.root, exist_ok=True)

    def path_for(
        self, key: str | Path, folder: Optional[str] = None, suffix: Optional[str] = None
    ) -> Path:
        """
        A unique file path with the given key. It's up to the client how to use it.
        """
        path_str = self.hash_func(key)

        if suffix:
            path_str += suffix
        path = Path(folder) / path_str if folder else Path(path_str)
        full_path = self.root / path

        return full_path

    def find(
        self, key: str | Path, folder: Optional[str] = None, suffix: Optional[str] = None
    ) -> Optional[Path]:
        cache_path = self.path_for(key, folder, suffix)
        return cache_path if path.exists(cache_path) else None

    def find_all(
        self, keys: List[str | Path], folder: Optional[str] = None, suffix: Optional[str] = None
    ) -> Dict[str | Path, Optional[Path]]:
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
