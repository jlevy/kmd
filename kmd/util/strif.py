"""
Strif is a tiny (<1000 loc) library of string and file utilities,
now updated for Python 3.10+.

More information: https://github.com/jlevy/strif
"""

import hashlib
import os
import random
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, List, Optional, Tuple

# A pre-opened handle to /dev/null.
DEV_NULL = open(os.devnull, "wb")

BACKUP_SUFFIX = ".bak"
TIMESTAMP_VAR = "{timestamp}"

_RANDOM = random.SystemRandom()
_RANDOM.seed()

#
# ---- Identifiers and base36 encodings ----


def new_uid(bits: int = 64) -> str:
    """
    A random alphanumeric value with at least the specified bits of randomness. We use base 36,
    i.e., not case sensitive. Note this makes it suitable for filenames even on case-insensitive disks.
    """
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    length = int(bits / 5.16) + 1  # log2(36) ≈ 5.17
    return "".join(_RANDOM.choices(chars, k=length))


def iso_timestamp(microseconds: bool = True) -> str:
    """
    ISO 8601 timestamp. Includes the Z for clarity that it is UTC.

    Example with microseconds: 2015-09-12T08:41:12.397217Z
    Example without microseconds: 2015-09-12T08:41:12Z
    """
    timespec = "microseconds" if microseconds else "seconds"
    return datetime.now(timezone.utc).isoformat(timespec=timespec).replace("+00:00", "Z")


def new_timestamped_uid(bits: int = 32) -> str:
    """
    A unique id that begins with an ISO timestamp followed by fractions of seconds and bits of
    randomness. The advantage of this is it sorts nicely by time, while still being unique.
    Example: 20150912T084555Z-378465-43vtwbx
    """
    timestamp = re.sub(r"[^\w.]", "", datetime.now().isoformat()).replace(".", "Z-")
    return f"{timestamp}-{new_uid(bits)}"


_NON_ALPHANUM_CHARS = re.compile(r"[^a-z0-9]+", re.IGNORECASE)


def clean_alphanum(string: str, max_length: Optional[int] = None) -> str:
    """
    Convert a string to a clean, readable identifier that includes the (first) alphanumeric
    characters of the given string.

    This mapping is for readability only, and so can easily have collisions on different inputs.
    """
    return _NON_ALPHANUM_CHARS.sub("_", string)[:max_length]


def clean_alphanum_hash(
    string: str, max_length: int = 64, max_hash_len: Optional[int] = None
) -> str:
    """
    Convert a string to a clean, readable identifier that includes the (first) alphanumeric
    characters of the given string.

    This includes a SHA1 hash so collisions are unlikely.
    """
    hash_str = hash_string_base36(string, algorithm="sha1")
    if max_hash_len:
        hash_str = hash_str[:max_hash_len]
    if max_length < len(hash_str) + 1:
        return hash_str
    else:
        clean_str = clean_alphanum(string, max_length=max_length - len(hash_str))
        return f"{clean_str}_{hash_str}"


def base36_encode(n: int) -> str:
    """
    Base 36 encode an integer.
    """
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    encoded = ""
    while n > 0:
        n, remainder = divmod(n, 36)
        encoded = chars[remainder] + encoded
    return encoded


def hash_string_base36(string: str, algorithm: str = "sha1") -> str:
    """
    Hash string and return in base 36, which is good for short, friendly identifiers.
    """
    h = hashlib.new(algorithm)
    h.update(string.encode("utf8"))
    return base36_encode(int.from_bytes(h.digest(), byteorder="big"))


#
# ---- Abbreviations ----


def abbreviate_str(string: str, max_len: Optional[int] = 80, indicator: str = "…") -> str:
    """
    Abbreviate a string, adding an indicator like an ellipsis if required. Set max_len to
    None or 0 not to truncate items.
    """
    if not string or not max_len or len(string) <= max_len:
        return string
    elif max_len <= len(indicator):
        return string[:max_len]
    else:
        return string[: max_len - len(indicator)] + indicator


def abbreviate_list(
    items: List[Any],
    max_items: int = 10,
    item_max_len: Optional[int] = 40,
    joiner: str = ", ",
    indicator: str = "…",
) -> str:
    """
    Abbreviate a list, truncating each element and adding an indicator at the end if the
    whole list was truncated. Set item_max_len to None or 0 not to truncate items.
    """
    if not items:
        return str(items)
    else:
        shortened = [abbreviate_str(str(item), max_len=item_max_len) for item in items[:max_items]]
        if len(items) > max_items:
            shortened.append(indicator)
        return joiner.join(shortened)


#
# ---- File operations ----


def _expand_backup_suffix(backup_suffix: str) -> str:
    return (
        backup_suffix.replace(TIMESTAMP_VAR, new_timestamped_uid())
        if TIMESTAMP_VAR in backup_suffix
        else backup_suffix
    )


def move_to_backup(path: str | Path, backup_suffix: Optional[str] = BACKUP_SUFFIX):
    """
    Move the given file or directory to the same name, with a backup suffix.
    If backup_suffix not supplied, move it to the extension ".bak".
    In backup_suffix, the string "{timestamp}", if present, will be replaced
    by a new_timestamped_uid(), allowing infinite numbers of timestamped backups.
    If backup_suffix is supplied and is None, don't do anything.

    Important:
    Without "{timestamp}", earlier backup files and directories, if they exist,
    will be clobbered!
    """
    path = Path(path)
    if backup_suffix and path.exists():
        backup_path = path.with_name(path.name + _expand_backup_suffix(backup_suffix))
        # Some messy corner cases need to be handled for existing backups.
        # TODO: Note if this is a directory, and we do this twice at once, there is a potential race
        # that could leave one backup inside the other.
        if backup_path.is_symlink():
            backup_path.unlink()
        elif backup_path.is_dir():
            shutil.rmtree(backup_path)
        shutil.move(str(path), str(backup_path))


def make_parent_dirs(path: str | Path, mode: int = 0o777) -> Path:
    """
    Ensure parent directories of a file are created as needed.
    """
    path = Path(path)
    parent = path.parent
    if parent:
        parent.mkdir(mode=mode, parents=True, exist_ok=True)
    return path


@contextmanager
def atomic_output_file(
    dest_path: str | Path,
    make_parents: bool = False,
    backup_suffix: Optional[str] = None,
    suffix: str = ".partial.%s",
) -> Generator[Path, None, None]:
    """
    A context manager for convenience in writing a file or directory in an atomic way. Set up
    a temporary name, then rename it after the operation is done, optionally making a backup of
    the previous file or directory, if present.
    """
    dest_path = Path(dest_path)
    if dest_path == Path(os.devnull):
        # Handle the (probably rare) case of writing to /dev/null.
        yield dest_path
    else:
        tmp_path = dest_path.with_name(dest_path.name + suffix % new_uid())
        if make_parents:
            make_parent_dirs(tmp_path)

        yield tmp_path

        # Note this is not in a finally block, so that result won't be renamed to final location
        # in case of abnormal exit.
        if not os.path.exists(tmp_path):
            raise IOError(
                "failure in writing file '%s': target file '%s' missing" % (dest_path, tmp_path)
            )
        if backup_suffix:
            move_to_backup(dest_path, backup_suffix=backup_suffix)
        # If the target already exists, and is a directory, it has to be removed.
        if os.path.isdir(dest_path):
            shutil.rmtree(dest_path)
        shutil.move(tmp_path, dest_path)


def temp_output_file(
    prefix: str = "tmp",
    suffix: str = "",
    dir: Optional[str | Path] = None,
    make_parents: bool = False,
    always_clean: bool = False,
) -> Generator[Tuple[int, Path], None, None]:
    """
    A context manager for convenience in creating a temporary file,
    which is deleted when exiting the context.

    Usage:
      with temp_output_file() as (fd, path):
        ...
    """
    if dir and make_parents:
        Path(dir).mkdir(parents=True, exist_ok=True)

    fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=str(dir) if dir else None)
    result = (fd, Path(path))

    def clean():
        try:
            rmtree_or_file(result[1], ignore_errors=True)
        except OSError:
            pass

    if always_clean:
        try:
            yield result
        finally:
            clean()
    else:
        yield result
        clean()


def temp_output_dir(
    prefix: str = "tmp",
    suffix: str = "",
    dir: Optional[str | Path] = None,
    make_parents: bool = False,
    always_clean: bool = False,
) -> Generator[Path, None, None]:
    """
    A context manager for convenience in creating a temporary directory,
    which is deleted when exiting the context.

    Usage:
      with temp_output_dir() as dirname:
        ...
    """
    if dir and make_parents:
        Path(dir).mkdir(parents=True, exist_ok=True)

    path = tempfile.mkdtemp(prefix=prefix, suffix=suffix, dir=str(dir) if dir else None)
    result = Path(path)

    def clean():
        try:
            rmtree_or_file(result, ignore_errors=True)
        except OSError:
            pass

    if always_clean:
        try:
            yield result
        finally:
            clean()
    else:
        yield result
        clean()


def copyfile_atomic(
    source_path: str | Path,
    dest_path: str | Path,
    make_parents: bool = False,
    backup_suffix: Optional[str] = None,
):
    """
    Copy file on local filesystem in an atomic way, so partial copies never exist. Preserves timestamps.
    """
    source_path = Path(source_path)
    dest_path = Path(dest_path)
    with atomic_output_file(
        dest_path, make_parents=make_parents, backup_suffix=backup_suffix
    ) as tmp_path:
        shutil.copyfile(str(source_path), str(tmp_path))
        mtime = source_path.stat().st_mtime
        os.utime(tmp_path, (mtime, mtime))


def copytree_atomic(
    source_path: str | Path,
    dest_path: str | Path,
    make_parents: bool = False,
    backup_suffix: Optional[str] = None,
    symlinks: bool = False,
):
    """
    Copy a file or directory recursively, and atomically, renaming file or top-level dir when done.
    Unlike shutil.copytree, this will not fail on a file.
    """
    source_path = Path(source_path)
    dest_path = Path(dest_path)
    if source_path.is_dir():
        with atomic_output_file(
            dest_path, make_parents=make_parents, backup_suffix=backup_suffix
        ) as tmp_path:
            shutil.copytree(str(source_path), str(tmp_path), symlinks=symlinks)
    else:
        copyfile_atomic(
            source_path, dest_path, make_parents=make_parents, backup_suffix=backup_suffix
        )


def movefile(
    source_path: str | Path,
    dest_path: str | Path,
    make_parents: bool = False,
    backup_suffix: Optional[str] = None,
):
    """
    Move file. With a few extra options.
    """
    source_path = Path(source_path)
    dest_path = Path(dest_path)
    if make_parents:
        make_parent_dirs(dest_path)
    move_to_backup(dest_path, backup_suffix=backup_suffix)
    shutil.move(str(source_path), str(dest_path))


def rmtree_or_file(path: str | Path, ignore_errors: bool = False):
    """
    rmtree fails on files or symlinks. This removes the target, whatever it is.
    """
    # TODO: Could add an rsync-based delete, as in
    # https://github.com/vivlabs/instaclone/blob/master/instaclone/instaclone.py#L127-L143
    if ignore_errors and not os.path.exists(path):
        return
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path, ignore_errors=ignore_errors)
    else:
        os.unlink(path)


def chmod_native(path: str | Path, mode_expression: str, recursive: bool = False):
    """
    This is ugly and will only work on POSIX, but the built-in Python os.chmod support
    is very minimal, and neither supports fast recursive chmod nor "+X" type expressions,
    both of which are slow for large trees. So just shell out.
    """
    path = Path(path)
    popenargs = ["chmod"]
    if recursive:
        popenargs.append("-R")
    popenargs.append(mode_expression)
    popenargs.append(str(path))
    subprocess.check_call(popenargs)