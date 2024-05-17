from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Optional

from strif import abbreviate_str
from kmd.util.text_formatting import clean_title

from kmd.util.url_utils import Url


class ItemType(Enum):
    """Kinds of items."""

    note = "note"
    question = "question"
    concept = "concept"
    answer = "answer"
    resource = "resource"
    export = "export"


class Format(Enum):
    """
    Format of the data in this item. This is the body data (not the file or metadata format).
    """

    url = "url"
    html = "html"
    markdown = "markdown"
    plaintext = "plaintext"
    pdf = "pdf"

    @classmethod
    def from_file_ext(cls, file_ext: str) -> "Format":
        file_ext_to_format = {
            FileExt.webpage.value: Format.html,
            FileExt.md.value: Format.markdown,
            FileExt.txt.value: Format.plaintext,
            FileExt.pdf.value: Format.pdf,
        }
        return file_ext_to_format[file_ext]

    def is_text(self) -> bool:
        return self not in [Format.pdf]

    def __str__(self):
        return self.name


class FileExt(Enum):
    """
    File type extensions for items.
    """

    pdf = "pdf"
    txt = "txt"
    md = "md"
    webpage = "webpage"

    @classmethod
    def from_format(cls, format: str | Format) -> Optional["FileExt"]:
        format_to_file_ext = {
            Format.html.value: FileExt.webpage,
            Format.url.value: FileExt.webpage,
            Format.markdown.value: FileExt.md,
            Format.plaintext.value: FileExt.txt,
            Format.pdf.value: FileExt.pdf,
        }

        return format_to_file_ext.get(str(format), None)

    @classmethod
    def is_text(cls, file_ext: str) -> bool:
        return file_ext in [cls.txt.value, cls.md.value, cls.webpage.value]

    def __str__(self):
        return self.name


UNTITLED = "Untitled"


@dataclass
class Item:
    """
    An Item is any piece of information we may wish to save or perform operations on, such as
    a text document, PDF or other resource, URL, etc.
    """

    type: ItemType
    title: Optional[str] = None
    url: Optional[Url] = None
    description: Optional[str] = None
    format: Optional[Format] = None
    file_ext: Optional[FileExt] = None

    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    # Content of the item.
    # Text items are in body. Large or binary items may be stored externally.
    body: Optional[str] = None
    external_path: Optional[str] = None
    is_binary: bool = False

    # Path to the item in the store, if it has been saved.
    store_path: Optional[str] = None

    # Optional additional metadata.
    extra: Optional[dict] = None

    NON_METADATA_FIELDS = ["file_ext", "body", "external_path", "is_binary", "store_path"]
    OPTIONAL_FIELDS = ["extra"]

    def update_modified_at(self):
        self.modified_at = datetime.now()

    def assert_body(self) -> None:
        if not self.body:
            raise ValueError(f"Expected body for item: {self}")

    def metadata(self) -> dict:
        """
        Metadata is all relevant non-None fields in easy-to-serialize form.
        Optional fields are omitted unless they are set.
        """
        item_dict = asdict(self)

        def serialize(v):
            return v.value if isinstance(v, Enum) else v

        item_dict = {
            k: serialize(v)  # Convert enums to strings for serialization.
            for k, v in item_dict.items()
            if v is not None and k not in self.NON_METADATA_FIELDS
        }
        for field in self.OPTIONAL_FIELDS:
            if field in item_dict and field is None:
                del item_dict[field]

        # Keep enum values as strings for simplicity with serialization to YAML.
        for field in ["type", "format"]:
            if item_dict.get(field):
                item_dict[field] = str(item_dict[field])

        return item_dict

    def get_title(self) -> str:
        """Get or infer title."""
        full_title = (
            self.title
            or self.url
            or self.description
            or (not self.is_binary and self.body)
            or UNTITLED
        )
        return clean_title(abbreviate_str(full_title, max_len=100, indicator="…"))

    def get_file_ext(self) -> FileExt:
        """Get or infer file extension."""

        if self.file_ext:
            return self.file_ext
        if self.is_binary and not self.file_ext:
            raise ValueError(f"Binary Items must have a file extension: {self}")
        inferred_ext = self.format and FileExt.from_format(self.format)
        if not inferred_ext:
            raise ValueError(f"Cannot infer file extension for Item: {self}")
        return inferred_ext

    def get_full_suffix(self) -> str:
        """Get the full file extension suffix for this item."""

        return f"{self.type.value}.{self.get_file_ext().value}"

    def body_text(self) -> str:
        if self.is_binary:
            raise ValueError("Cannot get text content of a binary Item")
        return self.body or ""

    def copy_with(self, **kwargs) -> "Item":
        """Copy item with the given field updates."""

        new_item = replace(self, **kwargs)
        # New should not have a store_path until it is saved.
        new_item.store_path = None
        new_item.created_at = datetime.now()
        new_item.modified_at = datetime.now()
        return new_item

    # Skip body in string representations to keep them manageable.

    def __abbreviated_self(self):
        item_dict = asdict(self)
        for field in ["title", "description", "body"]:
            item_dict[field] = abbreviate_str(item_dict[field], max_len=64)
        return item_dict

    def __str__(self):
        return str(self.__abbreviated_self())

    def __repr__(self):
        return repr(self.__abbreviated_self())
