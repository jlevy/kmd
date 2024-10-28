import sys
from pathlib import Path, PosixPath, WindowsPath
from typing import Any, cast, Optional, Tuple, Union

import regex
from frontmatter_format import add_default_yaml_representer
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from kmd.util.format_utils import fmt_path
from kmd.util.parse_shell_args import shell_quote
from kmd.util.url import is_url, Url


# Determine the base class for StorePath based on the operating system
if sys.platform == "win32":
    BasePath = WindowsPath
else:
    BasePath = PosixPath


class StorePathError(ValueError):
    """
    An error related to a StorePath.
    """


class InvalidStorePath(StorePathError):
    """
    Input was not a valid StorePath.
    """


_valid_store_name_re = regex.compile(r"^[\p{L}\p{N}_\.]+$", regex.UNICODE)

STORE_PATH_PREFIX = "@"
"""
Any store path can be @-mentioned, and for display we often use this to indicate
a path is a store path.
"""


class StorePath(BasePath):
    """
    A StorePath is a relative Path within a given scope (a directory we call a
    store) with the addition of some additional syntactic conveniences for parsing
    and displaying.

    Canonical form:
    The canonical form is `@folder1/folder2/filename.ext`.
    This indicates a file with the full path
    `folder1/folder2/filename.ext` within the current store.

    Alternative forms:
    - Regular relative paths like `folder1/folder2/filename.ext` are parsed as `@folder1/folder2/filename.ext`.
    - Paths starting like `@/folder1/folder2/filename.ext` are also parsed as `@folder1/folder2/filename.ext`.

    Optional store names:
    - To reference files with an explicit store name: `@~store_name/folder1/folder2/filename.ext`.
    - Store names must be alphanumeric (letters, digits, `_`, `.`).

    Paths containing spaces can be enclosed in single quotes:
    - `@'folder 1/folder 2/filename.ext'`
    - `@'~store_name/file with spaces.txt'`

    Restrictions:
    - Absolute paths like `/home/user/file.ext` are not allowed.
    - Empty or "." paths are not allowed.
    - `~store_name/` and `~store_name` are not valid StorePaths.
    """

    store_name: Optional[str] = None

    def __new__(
        cls,
        value: Union[str, Path],
        *more_parts: Union[str, Path],
        store_name: Optional[str] = None,
    ):
        """
        Create a new `StorePath` instance from a string representation as a relative path or in
        a standard format like `@folder/filename` or `@~store_name/folder/filename`.
        """

        # Parse a non-StorePath value
        # Pull out the store name from the first value.
        if isinstance(value, StorePath):
            parsed_path = value
            if not store_name:
                store_name = value.store_name
        else:
            parsed_path, parsed_store_name = cls.parse(value)
            if not store_name:
                store_name = parsed_store_name

        # Construct the path from all parts. This is important because this __new__ may
        # be called with same args as Path, e.g. from deepcopy, with several parts.
        path = Path(parsed_path, *more_parts)

        self = super().__new__(cls, *path.parts)
        self.store_name = store_name

        # XXX Ugly but not sure of a simpler way to initialize ourselves
        # exactly like a Path in __new__.
        self._raw_paths = path._raw_paths  # type: ignore
        self._load_parts()  # type: ignore

        return self

    def __init__(
        self,
        value: Union[str, Path],
        *rest: Union[str, Path],
        store_name: Optional[str] = None,
    ):
        pass

    @staticmethod
    def parse(value: str | Path) -> Tuple[Path, Optional[str]]:
        """
        Parse a string representation of the store path into a Path and store name
        (if any). The input should be a relative Path or a string representation
        that is a valid store path.
        """
        if not isinstance(value, (str, Path)):
            raise InvalidStorePath(f"Unexpected type for store path: {type(value)}: {value!r}")
        if isinstance(value, str) and is_url(value):
            raise InvalidStorePath(f"Expected a store path but got a URL: {value!r}")

        path = Path(value)
        if path.is_absolute():
            raise InvalidStorePath(f"Absolute store paths are not allowed: {value!r}")
        if path == Path("."):
            raise InvalidStorePath(f"Invalid store path: {value!r}")
        rest = str(value)
        if rest.startswith(STORE_PATH_PREFIX):
            rest = rest[1:]
        if rest.startswith("'"):
            # Path is enclosed in single quotes
            if rest.endswith("'"):
                quoted_path = rest[1:-1]
                rest = quoted_path
            else:
                raise InvalidStorePath(f"Unclosed single quote in store path: {value!r}")
        if rest.startswith("~"):
            # Store name is specified.
            rest = rest[1:]
            # Split rest into store_name and path.
            if "/" in rest:
                store_name, path_str = rest.split("/", 1)
            else:
                raise InvalidStorePath(f"Invalid store path: {value!r}")
            if (
                not store_name.strip()
                or not path_str.strip()
                or path_str.strip().startswith("/")
                or not _valid_store_name_re.match(store_name)
            ):
                raise InvalidStorePath(f"Invalid store path: {value!r}")
        else:
            store_name = None
            path_str = rest
            if path_str.startswith("/"):
                path_str = path_str[1:]

        return Path(path_str), store_name

    def __truediv__(self, key: Union[str, Path, "StorePath"]) -> "StorePath":
        if isinstance(key, Path):
            if key.is_absolute():
                raise StorePathError(f"Cannot join a StorePath with an absolute Path: {str(key)!r}")
            if isinstance(key, StorePath) and self.store_name != key.store_name:
                raise StorePathError(
                    f"Cannot join paths from different stores: {self!r} and {str(key)!r}"
                )
            key_parts = key.parts
        else:
            key_parts = (str(key),)
        new_parts = self.parts + key_parts
        return self.__class__(Path(*new_parts), store_name=self.store_name)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        # Use the handler to get the schema for the base Path type.
        path_schema = handler(BasePath)
        return core_schema.no_info_after_validator_function(
            cls.validate,
            path_schema,
        )

    @classmethod
    def validate(cls, value: Union[str, Path, "StorePath"]) -> "StorePath":
        if isinstance(value, StorePath):
            return value
        return cls(value)

    def resolve(self) -> Path:
        """
        If we resolve a StorePath, it must be a plain Path again, since StorePaths are relative.
        """
        return Path(self).resolve()

    def display_str(self) -> str:
        """
        String representation of the path with the `@` prefix and store name (if any)
        in canonical form.
        """
        path_str = str(self)
        if self.store_name:
            return STORE_PATH_PREFIX + shell_quote(f"~{self.store_name}/{path_str}")
        else:
            return STORE_PATH_PREFIX + shell_quote(path_str)

    def __str__(self) -> str:
        """
        The default str representation remains compatible with Path.
        """
        return super().__str__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self)!r})"

    def __eq__(self, other):
        if isinstance(other, StorePath):
            return super().__eq__(other) and self.store_name == other.store_name
        else:
            return False

    def __hash__(self):
        return hash((super().__str__(), self.store_name))


def fmt_store_path(store_path: str | Path | StorePath) -> str:
    return fmt_shell_path(StorePath(store_path))


def fmt_shell_path(store_path: str | Path | StorePath) -> str:
    if isinstance(store_path, StorePath):
        return store_path.display_str()
    else:
        return fmt_path(store_path)


Locator = Url | StorePath
"""
A reference to an external resource or an item in the store.
"""

InputArg = Locator | Path | str
"""
An argument to a command or action.
"""


def is_store_path(input_arg: InputArg) -> bool:
    if isinstance(input_arg, StorePath):
        return True
    elif isinstance(input_arg, Path):
        return False
    else:
        return not is_url(input_arg)


def resolve_at_path(path: str | Path | StorePath) -> Path | StorePath:
    """
    Resolve any string path that includes an @ prefix into a StorePath.
    Leaves other paths as Paths or StorePaths.
    """

    if isinstance(path, StorePath):
        return path
    elif isinstance(path, Path):
        return path
    elif path.startswith(STORE_PATH_PREFIX):
        return StorePath(path)
    else:
        return Path(path)


def as_url_or_path(input: str | Path) -> Path | Url:
    return cast(Url, str(input)) if is_url(str(input)) else cast(Path, input)


def _represent_store_path(dumper: Any, data: StorePath) -> Any:
    return dumper.represent_str(str(data))


add_default_yaml_representer(StorePath, _represent_store_path)


## Tests


def test_store_path():
    # Test creation with relative path
    sp1 = StorePath("some/relative/path")
    sp2 = StorePath("@some/relative/path")
    sp3 = StorePath("@/some/relative/path")
    assert isinstance(sp1, StorePath)
    assert isinstance(sp1, Path)
    assert sp1.store_name is None
    assert str(sp1) == "some/relative/path"
    assert sp1.display_str() == "@some/relative/path"
    assert sp1 == sp2
    assert sp1 == sp3

    # Test equality
    sp1 = StorePath("@path/to/file")
    sp2 = StorePath("path/to/file")
    sp3 = StorePath("path/to/file", store_name="store1")
    sp4 = StorePath("path/to/file", store_name="store1")
    assert sp1 == sp2
    assert sp3 == sp4
    assert sp1 != sp3

    # Test hash
    s = set()
    s.add(sp1)
    s.add(sp3)
    assert len(s) == 2
    s.add(sp2)
    assert len(s) == 2  # sp1 and sp2 are equal

    # Test that __str__, __repr__, and fmt_path don't raise an exception
    print([str(sp1), str(sp2), str(sp3), str(sp4)])
    print([repr(sp1), repr(sp2), repr(sp3), repr(sp4)])
    print(fmt_path(StorePath("store/path1")))
    print(repr(Path(StorePath("store/path1"))))

    # Test some invalid store paths
    try:
        StorePath("/absolute/path")
        assert False
    except InvalidStorePath as e:
        assert str(e) == "Absolute store paths are not allowed: '/absolute/path'"
    try:
        StorePath(".")
        assert False
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '.'"
    try:
        StorePath("")
        assert False
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: ''"

    try:
        StorePath("https://example.com")
        assert False
    except InvalidStorePath as e:
        assert str(e) == "Expected a store path but got a URL: 'https://example.com'"

    # Test with store name
    sp_with_store = StorePath("@~mystore/folder/file.txt")
    assert isinstance(sp_with_store, StorePath)
    assert sp_with_store.store_name == "mystore"
    assert str(sp_with_store) == "folder/file.txt"
    assert sp_with_store.display_str() == "@~mystore/folder/file.txt"

    # Test parsing '@folder/file.txt'
    sp2 = StorePath("@folder/file.txt")
    assert sp2.store_name is None
    assert str(sp2) == "folder/file.txt"
    assert sp2.display_str() == "@folder/file.txt"

    # Test parsing '@/folder/file.txt'
    sp3 = StorePath("@/folder/file.txt")
    assert sp3.store_name is None
    assert str(sp3) == "folder/file.txt"  # Leading '/' is removed
    assert sp3.display_str() == "@folder/file.txt"

    # Test parsing '@~/folder/file.txt' (invalid, missing store name)
    try:
        StorePath("@~/folder/file.txt")
        assert False
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '@~/folder/file.txt'"

    # Test invalid store name
    try:
        StorePath("@~store-name/folder/file.txt")  # 'store-name' with hyphen is invalid
        assert False
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '@~store-name/folder/file.txt'"

    # Test that '~store_name/' and '~store_name' are invalid
    try:
        StorePath("~store_name/")
        assert False
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '~store_name/'"

    try:
        StorePath("~store_name")
        assert False
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '~store_name'"

    # Test that '@~store_name' is invalid
    try:
        StorePath("@~store_name")
        assert False
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '@~store_name'"

    # Test paths with spaces enclosed in single quotes
    sp_spaces = StorePath("@'folder 1/folder 2/filename.ext'")
    assert isinstance(sp_spaces, StorePath)
    assert sp_spaces.store_name is None
    assert str(sp_spaces) == "folder 1/folder 2/filename.ext"
    assert sp_spaces.display_str() == "@'folder 1/folder 2/filename.ext'"

    sp_spaces2 = StorePath("@'/folder 1/folder 2/filename.ext'")
    assert sp_spaces == sp_spaces2

    sp_spaces3 = StorePath("@'~store_name/file with spaces.txt'")
    assert sp_spaces3.store_name == "store_name"
    assert str(sp_spaces3) == "file with spaces.txt"
    assert sp_spaces3.display_str() == "@'~store_name/file with spaces.txt'"

    # Test unclosed single quote
    try:
        StorePath("@'folder/filename.ext")
        assert False
    except InvalidStorePath as e:
        assert str(e) == 'Unclosed single quote in store path: "@\'folder/filename.ext"'
    try:
        StorePath("@'folder/filename.ext' extra")
        assert False
    except InvalidStorePath as e:
        assert str(e) == "Unclosed single quote in store path: \"@'folder/filename.ext' extra\""

    # Path / StorePath
    combined = Path("base/path") / StorePath("@some/relative/path")
    assert isinstance(combined, Path)
    assert combined == Path("base/path/some/relative/path")

    # StorePath / relative Path
    combined = StorePath("base/store/path") / Path("some/relative/path")
    assert isinstance(combined, StorePath)
    assert combined == StorePath("base/store/path/some/relative/path")
    assert combined.store_name is None

    # StorePath / absolute Path
    try:
        combined = sp1 / Path("/absolute/path")
        assert False
    except StorePathError as e:
        assert str(e) == "Cannot join a StorePath with an absolute Path: '/absolute/path'"

    # StorePath / StorePath
    combined = StorePath("store/path1") / StorePath("store/path2")
    assert isinstance(combined, StorePath)
    assert combined == StorePath("store/path1/store/path2")
    assert combined.store_name is None

    # Instantiating Paths
    assert Path(StorePath("store/path1")).resolve() == Path("store/path1").resolve()
