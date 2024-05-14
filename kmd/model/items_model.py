from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from enum import Enum
import re
from typing import Optional

from strif import abbreviate_str

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
    """Format of the data in this item."""

    url = "url"
    html = "html"
    markdown = "markdown"
    plaintext = "plaintext"
    pdf = "pdf"

    def __str__(self):
        return self.name


class FileExt(Enum):
    """File type extensions for items."""

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

    def __str__(self):
        return self.name


UNTITLED = "Untitled"


@dataclass
class Item:
    """
    An item that we may operate on. Could be one of various types, and may be persisted on disk or
    as a database record.
    """

    type: ItemType
    title: Optional[str] = None
    url: Optional[Url] = None
    description: Optional[str] = None
    format: Optional[Format] = None
    file_ext: Optional[FileExt] = None

    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    body: Optional[str] = None
    external_path: Optional[str] = None
    is_binary: bool = False

    # Optional additional metadata.
    extra: Optional[dict] = None

    NON_METADATA_FIELDS = ["file_ext", "body", "external_path", "is_binary"]
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
        item_dict = {
            k: v
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
        return re.sub(r"\s+", " ", abbreviate_str(full_title, max_len=100)).strip()

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
