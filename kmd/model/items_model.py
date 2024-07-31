"""
The data model for Items and their file formats.
"""

from dataclasses import asdict, dataclass, field, fields, replace
import dataclasses
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Tuple
from kmd.config.logger import get_logger
from kmd.model.graph_model import Link, Node
from kmd.model.media_model import MediaMetadata
from kmd.util.time_util import iso_format_z
from kmd.file_storage.yaml_util import from_yaml_string
from kmd.model.canon_concept import canonicalize_concept
from kmd.model.canon_url import canonicalize_url
from kmd.model.errors_model import FileFormatError
from kmd.model.locators import Locator
from kmd.text_formatting.markdown_util import markdown_to_html
from kmd.text_formatting.text_formatting import (
    abbreviate_on_words,
    abbreviate_phrase_in_middle,
    clean_title,
    html_to_plaintext,
    plaintext_to_html,
)
from kmd.util.obj_utils import abbreviate_obj
from kmd.util.url import Url


log = get_logger(__name__)  # type: ignore


class ItemType(Enum):
    """Kinds of items."""

    note = "note"
    question = "question"
    concept = "concept"
    answer = "answer"
    resource = "resource"
    config = "config"
    export = "export"
    instruction = "instruction"
    extension = "extension"


class Format(Enum):
    """
    Format of the data in this item. This is the body data format (or "url" for a URL resource).
    """

    url = "url"
    html = "html"
    markdown = "markdown"  # Should be simple and clean Markdown that we can use with LLMs.
    md_html = "md_html"  # Markdown with HTML. Helps to know this to avoid using with LLMs and auto-formatting.
    plaintext = "plaintext"
    pdf = "pdf"
    yaml = "yaml"
    python = "python"

    def is_text(self) -> bool:
        return self not in [Format.pdf]

    @classmethod
    def guess_by_file_ext(cls, file_ext: "FileExt") -> Optional["Format"]:
        """
        Guess the format for a given file extension. Doesn't work for .yml since that could be
        various formats. This doesn't need to be perfect, mainly used when importing files.
        """
        ext_to_format = {
            FileExt.html.value: Format.html,
            FileExt.md.value: Format.markdown,
            FileExt.txt.value: Format.plaintext,
            FileExt.pdf.value: Format.pdf,
            FileExt.py.value: Format.python,
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
    py = "py"

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
            Format.md_html.value: FileExt.md,
            Format.plaintext.value: FileExt.txt,
            Format.pdf.value: FileExt.pdf,
            Format.yaml.value: FileExt.yml,
            Format.python.value: FileExt.py,
        }

        return format_to_file_ext.get(str(format), None)

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class ItemId:
    """
    Represents the identity of an item. Used as a key to determine when to treat two items as
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

    derived_from: Optional[list[Locator]] = None

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

    # TODO: Consider adding aliases and tags. See also Obsidian frontmatter format:
    # https://help.obsidian.md/Editing+and+formatting/Properties#Default%20properties

    # Content of the item.
    # Text items are in body. Large or binary items may be stored externally.
    body: Optional[str] = None
    external_path: Optional[str] = None
    is_binary: bool = False

    # Path to the item in the store, if it has been saved.
    store_path: Optional[str] = None

    # Optionally, relations to other items, including any time this item is derived from.
    relations: ItemRelations = field(default_factory=ItemRelations)

    # Optionally, a URL to a thumbnail image for this item.
    thumbnail_url: Optional[Url] = None

    # Optional additional metadata.
    extra: Optional[dict] = None

    # These fields we don't want in YAML frontmatter.
    # We don't include store_path as it's redundant with the filename.
    NON_METADATA_FIELDS = ["file_ext", "body", "external_path", "is_binary", "store_path"]

    def __post_init__(self):
        assert type(self.type) == ItemType
        assert self.format is None or type(self.format) == Format
        assert self.file_ext is None or type(self.file_ext) == FileExt

        if not isinstance(self.relations, ItemRelations):
            self.relations = ItemRelations(**self.relations)

    @classmethod
    def from_dict(cls, item_dict: dict[str, Any], **kwargs) -> "Item":
        """
        Deserialize fields from a dict that may incude string and dict values.
        """
        item_dict = {**item_dict, **kwargs}

        # These are the enum and dataclass fields.
        try:
            type = ItemType(item_dict["type"])
            format = Format(item_dict["format"]) if "format" in item_dict else None
            file_ext = FileExt(item_dict["file_ext"]) if "file_ext" in item_dict else None
            body = item_dict.get("body")
            relations = (
                ItemRelations(**item_dict["relations"])
                if "relations" in item_dict
                else ItemRelations()
            )
            store_path = item_dict.get("store_path")
            # TODO: created_at and modified_at could be handled here too.
        except KeyError as e:
            raise ValueError(f"Error deserializing Item: {e}")

        # Other fields are basic strings or dicts.
        other_metadata = {
            key: value
            for key, value in item_dict.items()
            if key not in ["type", "format", "file_ext", "body", "relations", "store_path"]
        }

        return Item(
            type=type,
            format=format,
            file_ext=file_ext,
            body=body,
            relations=relations,
            **other_metadata,
            store_path=store_path,
        )

    @classmethod
    def from_media_metadata(cls, media_metadata: MediaMetadata) -> "Item":
        """
        Create an Item instance from MediaMetadata.
        """
        created_at = (
            datetime.combine(media_metadata.upload_date, datetime.min.time())
            if media_metadata.upload_date
            else datetime.now()
        )
        return cls(
            type=ItemType.resource,
            format=Format.url,
            title=media_metadata.title,
            url=media_metadata.url,
            description=media_metadata.description,
            thumbnail_url=media_metadata.thumbnail_url,
            created_at=created_at,
            extra={
                "media_id": media_metadata.media_id,
                "media_service": media_metadata.media_service,
                "upload_date": media_metadata.upload_date,
                "channel_url": media_metadata.channel_url,
                "view_count": media_metadata.view_count,
                "duration": media_metadata.duration,
                "heatmap": media_metadata.heatmap,
            },
        )

    def doc_id(self) -> str:
        """
        Semi-permanent id for the document. Currently just the store path.
        """
        if not self.store_path:
            raise ValueError("Cannot get doc id for an item that has not been saved")
        return str(self.store_path)

    def update_modified_at(self):
        self.modified_at = datetime.now()

    def metadata(self, datetime_as_str: bool = False) -> dict[str, Any]:
        """
        Metadata is all relevant non-None fields in easy-to-serialize form.
        Optional fields are omitted unless they are set.
        """
        item_dict = asdict(self)

        def serialize(v):
            return v.value if isinstance(v, Enum) else v

        # It's simpler to keep enum values as strings for simplicity with
        # serialization to YAML and JSON.
        item_dict = {
            k: serialize(v)  # Convert enums to strings for serialization.
            for k, v in item_dict.items()
            if v is not None and k not in self.NON_METADATA_FIELDS
        }

        # Sometimes it's also better to serialize datetimes as strings.
        if datetime_as_str:
            for f, v in item_dict.items():
                if isinstance(v, datetime):
                    item_dict[f] = iso_format_z(v)

        return item_dict

    def abbrev_title(self, max_len: int = 100) -> str:
        """
        Get or infer title.
        """
        title_raw_text = (
            self.title
            or self.url
            or self.description
            or (not self.is_binary and self.body)
            or UNTITLED
        )

        return clean_title(abbreviate_phrase_in_middle(html_to_plaintext(title_raw_text), max_len))

    def abbrev_description(self, max_len: int = 1000) -> str:
        """
        Get or infer description.
        """
        return abbreviate_on_words(html_to_plaintext(self.description or self.body or ""), max_len)

    def read_as_config(self) -> Any:
        """
        If it is a config Item, return the parsed YAML.
        """
        if not self.type == ItemType.config:
            raise FileFormatError(f"Item is not a config: {self}")
        if not self.body:
            raise FileFormatError(f"Config item has no body: {self}")
        if self.format != Format.yaml:
            raise FileFormatError(f"Config item is not YAML: {self.format}: {self}")
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

        # Python files cannot have more than one . in them.
        if self.type == ItemType.extension:
            return f"{FileExt.py.value}"
        else:
            return f"{self.type.value}.{self.get_file_ext().value}"

    def body_text(self) -> str:
        if self.is_binary:
            raise ValueError("Cannot get text content of a binary Item")
        return self.body or ""

    def body_as_html(self) -> str:
        if self.format == Format.html:
            return self.body_text()
        elif self.format == Format.plaintext:
            return plaintext_to_html(self.body_text())
        elif self.format == Format.markdown or self.format == Format.md_html:
            return markdown_to_html(self.body_text())

        raise ValueError(f"Cannot convert item of type {self.format} to HTML: {self}")

    def is_url_resource(self) -> bool:
        return self.type == ItemType.resource and self.format == Format.url and self.url is not None

    def _merge_fields(self, other: Optional["Item"] = None, **kwargs) -> dict:
        defaults = {"store_path": None, "created_at": datetime.now(), "modified_at": datetime.now()}
        base_fields = asdict(self)

        if other:
            base_fields.update(asdict(other))
            base_fields["extra"] = {**(self.extra or {}), **(other.extra or {})}

        base_fields.update(defaults)
        base_fields.update(kwargs)

        return base_fields

    def new_copy_with(self, **kwargs) -> "Item":
        """
        Copy item with the given field updates. Resets store_path and updates timestamps
        if they are not set.
        """
        new_fields = self._merge_fields(**kwargs)
        return Item(**new_fields)

    def merged_copy(self, other: "Item") -> "Item":
        """
        Copy item, merging in fields from another, with the other item's fields
        taking precedence. Resets store_path and updates timestamps if they are not set.
        """
        merged_fields = self._merge_fields(other)
        return Item(**merged_fields)

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
        metadata_matches = replace(
            self,
            created_at=other.created_at,
            modified_at=other.modified_at,
            store_path=other.store_path,
            body=None,
        ) == replace(other, body=None)
        # Trailing newlines don't matter.
        body_matches = (
            self.is_binary == other.is_binary and self.body == other.body
        ) or self.body_text().rstrip() == other.body_text().rstrip()
        return metadata_matches and body_matches

    def as_node_links(self) -> Tuple[Node, List[Link]]:
        """
        Node and Links for this item.
        """
        if not self.store_path:
            raise ValueError(f"Expected store path to convert item to node/links: {self}")

        node = Node(
            id=self.store_path,
            type=self.type.name,
            title=self.title or UNTITLED,
            description=self.description,
            body=None,  # Skip for now, might add if we find it useful.
            url=str(self.url) if self.url else None,
            thumbnail_url=self.thumbnail_url,
        )

        links = []
        for f in fields(ItemRelations):
            relation_list = getattr(self.relations, f.name)
            if relation_list:
                for target in relation_list:
                    links.append(
                        Link(source=self.store_path, target=str(target), relationship=f.name)
                    )

        # TODO: Extract other relations here from the content.

        return node, links

    def __str__(self):
        return abbreviate_obj(self)


# Some refletion magic so the order of the YAML metadata for an item will match
# the order of the fields here.
ITEM_FIELDS = [f.name for f in dataclasses.fields(Item)]
