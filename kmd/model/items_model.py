"""
The data model for Items and their file formats.
"""

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from strif import abbreviate_str
from kmd.file_storage.yaml_util import from_yaml_string
from kmd.model.canon_concept import canonicalize_concept
from kmd.model.canon_url import canonicalize_url
from kmd.model.locators import Locator
from kmd.text_handling.markdown_util import markdown_to_html
from kmd.text_handling.text_formatting import (
    abbreviate_on_words,
    clean_title,
    plaintext_to_html,
)
from kmd.util.url import Url


class ItemType(Enum):
    """Kinds of items."""

    note = "note"
    question = "question"
    concept = "concept"
    answer = "answer"
    resource = "resource"
    config = "config"
    export = "export"


class Format(Enum):
    """
    Format of the data in this item. This is the body data format (or "url" for a URL resource).
    """

    url = "url"
    html = "html"
    markdown = "markdown"
    plaintext = "plaintext"
    pdf = "pdf"
    yaml = "yaml"

    def is_text(self) -> bool:
        return self not in [Format.pdf]

    @classmethod
    def for_file_ext(cls, file_ext: "FileExt") -> Optional["Format"]:
        """
        Infer the format for a given file extension. Doesn't work for .yml since that could be
        various formats.
        """
        ext_to_format = {
            FileExt.html.value: Format.html,
            FileExt.md.value: Format.markdown,
            FileExt.txt.value: Format.plaintext,
            FileExt.pdf.value: Format.pdf,
        }
        return ext_to_format.get(file_ext.value, None)

    def __str__(self):
        return self.name


class FileExt(Enum):
    """
    File type extensions for items.
    """

    pdf = "pdf"
    txt = "txt"
    md = "md"
    yml = "yml"
    html = "html"

    def is_text(self) -> bool:
        return self in [self.txt, self.md, self.yml, self.html]

    @classmethod
    def for_format(cls, format: str | Format) -> Optional["FileExt"]:
        """
        Infer the file extension for a given format.
        """
        format_to_file_ext = {
            Format.html.value: FileExt.html,
            Format.url.value: FileExt.yml,
            Format.markdown.value: FileExt.md,
            Format.plaintext.value: FileExt.txt,
            Format.pdf.value: FileExt.pdf,
            Format.yaml.value: FileExt.yml,
        }

        return format_to_file_ext.get(str(format), None)

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class ItemId:
    """
    Represents the identity of an an item. Used as a key to determine when to treat two items as
    the same object (same URL, same concept, etc.).
    """

    type: ItemType
    format: Format
    value: str

    def __str__(self):
        return f"id:{self.type.value}:{self.format.value}:{self.value}"


@dataclass
class ItemRelations:
    """
    Relations of a given item to other items.
    """

    derived_from: Optional[Locator] = None

    # TODO: Other relations.
    # citations: Optional[list[Locator]] = None
    # named_entities: Optional[list[Locator]] = None
    # related_concepts: Optional[list[Locator]] = None


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

    # Optionally, relations to other items, including any time this item is derived from.
    relations: ItemRelations = field(default_factory=ItemRelations)

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

    def get_title(self, max_len: int = 100) -> str:
        """
        Get or infer title.
        """
        full_title = (
            self.title
            or self.url
            or self.description
            or (not self.is_binary and self.body)
            or UNTITLED
        )
        return clean_title(
            abbreviate_on_words(
                abbreviate_str(full_title, max_len=max_len + 2, indicator="…"), max_len=max_len
            )
        )

    def read_as_config(self) -> Any:
        """
        If it is a config Item, return the parsed YAML.
        """
        if not self.type == ItemType.config:
            raise ValueError(f"Item is not a config: {self}")
        if not self.body:
            raise ValueError(f"Config item has no body: {self}")
        if self.format != Format.yaml.value:
            raise ValueError(f"Config item is not YAML: {self.format}: {self}")
        return from_yaml_string(self.body)

    def get_file_ext(self) -> FileExt:
        """
        Get or infer file extension.
        """
        if self.file_ext:
            return self.file_ext
        if self.is_binary and not self.file_ext:
            raise ValueError(f"Binary Items must have a file extension: {self}")
        inferred_ext = self.format and FileExt.for_format(self.format)
        if not inferred_ext:
            raise ValueError(f"Cannot infer file extension for Item: {self}")
        return inferred_ext

    def get_full_suffix(self) -> str:
        """
        Get the full file extension suffix (e.g. "note.md") for this item.
        """

        return f"{self.type.value}.{self.get_file_ext().value}"

    def body_text(self) -> str:
        if self.is_binary:
            raise ValueError("Cannot get text content of a binary Item")
        return self.body or ""

    def body_as_html(self) -> str:
        if str(self.format) == str(Format.html):
            return self.body_text()
        elif str(self.format) == str(Format.plaintext):
            return plaintext_to_html(self.body_text())
        elif str(self.format) == str(Format.markdown):
            return markdown_to_html(self.body_text())

        raise ValueError(f"Cannot convert item of type {self.format} to HTML: {self}")

    def is_url_resource(self) -> bool:
        return (
            self.type == ItemType.resource
            and self.format == Format.url.value
            and self.url is not None
        )

    def new_copy_with(self, **kwargs) -> "Item":
        """
        Copy item with the given field updates. Resets store_path and updates timestamps.
        """
        new_item = replace(self, **kwargs)
        new_item.store_path = None
        new_item.created_at = datetime.now()
        new_item.modified_at = datetime.now()
        return new_item

    def derived_copy(self, **kwargs) -> "Item":
        """
        Same as `new_copy_with()`, but also updates `derived_from` relation.
        """
        if not self.store_path:
            raise ValueError(f"Cannot derive from an item that has not been saved: {self}")
        new_item = self.new_copy_with(**kwargs)
        new_item.update_relations(derived_from=[self.store_path])
        return new_item

    def update_relations(self, **relations: List[str]) -> ItemRelations:
        """
        Update relations with the given field updates.
        """
        self.relations = self.relations or ItemRelations()
        self.relations = replace(self.relations, **relations)
        return self.relations

    def item_id(self) -> Optional[ItemId]:
        """
        Return identity of the item, or None if it should be treated as unique.
        """
        item_id = None

        if self.type == ItemType.resource and self.format == Format.url and self.url:
            item_id = ItemId(self.type, self.format, canonicalize_url(self.url))
        elif self.type == ItemType.concept and self.title:
            item_id = ItemId(self.type, Format.plaintext, canonicalize_concept(self.title))

        return item_id

    def content_equals(self, other: "Item") -> bool:
        """
        Check if two items have identical content, ignoring timestamps and store path.
        """
        return (
            replace(
                self,
                created_at=other.created_at,
                modified_at=other.modified_at,
                store_path=other.store_path,
            )
            == other
        )

    def _abbreviated_self(self):
        return {
            k: repr(
                abbreviate_str(
                    str(v.value) if isinstance(v, Enum) else str(v),
                    max_len=64,
                    indicator="[…]",
                )
            )
            for k, v in sorted(asdict(self).items())
            if v is not None
        }

    def __str__(self):
        """
        Abbreviate long fields and omit Nones for readability.
        """
        summary = ", ".join([f"{k}={v}" for k, v in self._abbreviated_self().items()])
        return f"Item({summary})"
