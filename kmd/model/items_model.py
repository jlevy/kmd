"""
The data model for Items and their file formats.
"""

from dataclasses import asdict, dataclass, field, fields, replace
import dataclasses
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Type, TypeVar, Dict
from slugify import slugify
from kmd.config.logger import get_logger
from kmd.model.file_formats_model import FileExt, Format
from kmd.model.media_model import MediaMetadata
from kmd.model.operations_model import Operation, OperationSummary, Source
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
    fmt_path,
    html_to_plaintext,
    plaintext_to_html,
)
from kmd.util.obj_utils import abbreviate_obj
from kmd.util.url import Url


log = get_logger(__name__)  # type: ignore


T = TypeVar("T")


class ItemType(Enum):
    """Kinds of items."""

    doc = "doc"
    concept = "concept"
    resource = "resource"
    config = "config"
    export = "export"
    instruction = "instruction"
    extension = "extension"


class State(Enum):
    """
    Review state of an item. Draft is default. Transient is used for items that may be
    safely auto-archived.
    """

    draft = "draft"
    reviewed = "reviewed"
    transient = "transient"


class IdType(Enum):
    """
    Types of identity checks.
    """

    url = "url"
    concept = "concept"
    source = "source"


@dataclass(frozen=True)
class ItemId:
    """
    Represents the identity of an item. Used as a key to determine when to treat two items as
    the same object. This could be the same URL, the same concept, or the same source, by which
    we mean the item is the output of the same action on the exact same inputs).
    """

    type: ItemType
    id_type: IdType
    value: str

    def id_str(self):
        return f"id:{self.id_type.value}:{self.value.replace(' ', '_')}"

    def __str__(self):
        return self.id_str()

    @classmethod
    def for_item(cls, item: "Item") -> Optional["ItemId"]:
        item_id = None
        if item.type == ItemType.resource and item.format == Format.url and item.url:
            item_id = ItemId(item.type, IdType.url, canonicalize_url(item.url))
        elif item.type == ItemType.concept and item.title:
            item_id = ItemId(item.type, IdType.concept, canonicalize_concept(item.title))
        elif item.source:
            item_id = ItemId(item.type, IdType.source, item.source.as_str())

        return item_id


@dataclass
class ItemRelations:
    """
    Relations of a given item to other items.
    """

    derived_from: Optional[List[Locator]] = None

    # TODO: Other relations.
    # citations: Optional[List[Locator]] = None
    # named_entities: Optional[List[Locator]] = None
    # related_concepts: Optional[List[Locator]] = None


UNTITLED = "Untitled"

SLUG_MAX_LEN = 64


@dataclass
class Item:
    """
    An Item is any piece of information we may wish to save or perform operations on, such as
    a text document, PDF or other resource, URL, etc.
    """

    type: ItemType
    state: State = State.draft
    title: Optional[str] = None
    url: Optional[Url] = None
    description: Optional[str] = None
    format: Optional[Format] = None
    file_ext: Optional[FileExt] = None

    created_at: datetime = field(default_factory=datetime.now)
    modified_at: Optional[datetime] = None

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

    # The operation that created this item.
    source: Optional[Source] = None

    # Optionally, a history of operations.
    history: Optional[List[OperationSummary]] = None

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
    def from_dict(cls, item_dict: Dict[str, Any], **kwargs) -> "Item":
        """
        Deserialize fields from a dict that may incude string and dict values.
        """
        item_dict = {**item_dict, **kwargs}

        info_prefix = f"{fmt_path(item_dict['store_path'])}: " if "store_path" in item_dict else ""

        # Metadata formats might change over time so it's important to gracefully handle issues.
        def set_field(key: str, default: Any, cls: Type[T]) -> T:
            try:
                if key in item_dict:
                    return cls(item_dict[key])  # type: ignore
                else:
                    return default
            except (KeyError, ValueError) as e:
                log.warning(
                    "Error reading %sfield `%s` so using default `%s`: %s: %s",
                    info_prefix,
                    key,
                    default,
                    e,
                    item_dict,
                )
                return default

        # These are the enum and dataclass fields.
        type = set_field("type", ItemType.doc, ItemType)
        state = set_field("state", State.draft, State)
        format = set_field("format", None, Format)
        file_ext = set_field("file_ext", None, FileExt)
        source = set_field("source", None, Source.from_dict)  # type: ignore

        body = item_dict.get("body")
        history = [OperationSummary(**op) for op in item_dict.get("history", [])]
        relations = (
            ItemRelations(**item_dict["relations"]) if "relations" in item_dict else ItemRelations()
        )
        store_path = item_dict.get("store_path")

        # Other fields are basic strings or dicts.
        excluded_fields = [
            "type",
            "state",
            "format",
            "file_ext",
            "body",
            "source",
            "history",
            "relations",
            "store_path",
        ]
        all_fields = [f.name for f in fields(cls)]
        allowed_fields = [f for f in all_fields if f not in excluded_fields]
        other_metadata = {key: value for key, value in item_dict.items() if key in allowed_fields}
        unexpected_metadata = {
            key: value for key, value in item_dict.items() if key not in all_fields
        }
        if unexpected_metadata:
            log.info(
                "Skipping unexpected metadata on item: %s: %s", info_prefix, unexpected_metadata
            )

        return Item(
            type=type,
            state=state,
            format=format,
            file_ext=file_ext,
            body=body,
            relations=relations,
            source=source,
            history=history,
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

    def metadata(self, datetime_as_str: bool = False) -> dict[str, Any]:
        """
        Metadata is all relevant non-None fields in easy-to-serialize form.
        Optional fields are omitted unless they are set.
        """

        item_dict = asdict(self)

        # Special case for prettier serialization of input path/hash.
        if self.source:
            item_dict["source"] = self.source.as_dict()

        def serialize(v):
            if isinstance(v, Enum):
                return v.value
            elif isinstance(v, Operation):
                # Special case for prettier display of inputs.
                return v.as_dict()
            else:
                return v

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

    def path_or_title(self) -> str:
        """
        Get the path or fall back to the title of the item.
        """
        return self.store_path or self.abbrev_title()

    def abbrev_title(self, max_len: int = 100) -> str:
        """
        Get or infer title. Optionally, include the last operation as a parenthetical
        at the end of the title.
        """
        title_raw_text = (
            self.title
            or self.url
            or self.description
            or (not self.is_binary and self.body)
            or UNTITLED
        )

        # For notes, exports, etc but not for concepts, add a suffix indicating the
        # last operation, if there was one.
        suffix = ""
        with_last_op = self.type not in [ItemType.concept, ItemType.resource]
        last_op = with_last_op and self.history and self.history[-1].action_name
        if last_op:
            suffix = f" ({last_op})"

        shorter_len = min(max_len, max(max_len - len(suffix), 20))
        clean_text = clean_title(
            abbreviate_phrase_in_middle(html_to_plaintext(title_raw_text), shorter_len)
        )

        final_text = clean_text
        if len(suffix) + len(clean_text) <= max_len:
            final_text += suffix

        return final_text

    def title_slug(self, max_len: int = SLUG_MAX_LEN) -> str:
        """
        Get a readable slugified version of the title for this item (may not be unique).
        """
        title = self.abbrev_title(max_len=max_len)
        slug = slugify(title, max_length=max_len, separator="_")
        return slug

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

    def full_text(self) -> str:
        """
        Get the full text of the item, including any title, description, and body.
        Use for embeddings.
        """
        parts = [self.title, self.description, self.body_text().strip()]
        return "\n\n".join(part for part in parts if part)

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

    def _merge_fields(
        self, other: Optional["Item"] = None, update_timestamp: bool = False, **kwargs
    ) -> dict:
        timestamp = datetime.now() if update_timestamp else None
        overrides = {"store_path": None, "created_at": timestamp, "modified_at": None}

        # asdict() creates dicts recursively so using __annotations__ to do a shallow copy.
        fields = {field: getattr(self, field) for field in self.__annotations__}

        if other:
            for field in other.__annotations__:
                fields[field] = getattr(other, field)
            fields["extra"] = {**(self.extra or {}), **(other.extra or {})}

        fields.update(overrides)
        fields.update(kwargs)

        return fields

    def new_copy_with(self, update_timestamp: bool = True, **kwargs) -> "Item":
        """
        Copy item with the given field updates. Resets store_path to None. Updates
        created time if requested.
        """
        new_fields = self._merge_fields(update_timestamp=update_timestamp, **kwargs)
        return Item(**new_fields)

    def merged_copy(self, other: "Item") -> "Item":
        """
        Copy item, merging in fields from another, with the other item's fields
        taking precedence. Resets store_path to None.
        """
        merged_fields = self._merge_fields(other, update_timestamp=False)
        return Item(**merged_fields)

    def derived_copy(self, **kwargs) -> "Item":
        """
        Same as `new_copy_with()`, but also updates `derived_from` relation.
        """
        if not self.store_path:
            raise ValueError(f"Cannot derive from an item that has not been saved: {self}")

        new_item = self.new_copy_with(update_timestamp=True, **kwargs)
        new_item.update_relations(derived_from=[self.store_path])

        return new_item

    def update_relations(self, **relations: List[str]) -> ItemRelations:
        """
        Update relations with the given field updates.
        """
        self.relations = self.relations or ItemRelations()
        self.relations = replace(self.relations, **relations)
        return self.relations

    def update_history(self, source: Source) -> None:
        """
        Update the history of the item with the given operation.
        """
        self.source = source
        self.add_to_history(source.operation.summary())

    def item_id(self) -> Optional[ItemId]:
        """
        Return identity of the item, or None if it should be treated as unique.
        """
        return ItemId.for_item(self)

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

    def add_to_history(self, operation_summary: OperationSummary):
        if not self.history:
            self.history = []
        self.history.append(operation_summary)

    def __str__(self):
        return abbreviate_obj(self)


# Some refletion magic so the order of the YAML metadata for an item will match
# the order of the fields here.
ITEM_FIELDS = [f.name for f in dataclasses.fields(Item)]
