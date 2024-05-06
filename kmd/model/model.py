from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Optional, Set
import inflect

from slugify import slugify


@dataclass
class Action:
    name: str
    description: str
    implementation: str = "builtin"
    model: Optional[str] = None
    template: Optional[str] = None
    system_message: Optional[str] = None


class ItemType(Enum):
    """Kinds of Items."""

    note = "note"
    question = "question"
    concept = "concept"
    answer = "answer"
    resource = "resource"


_inflect = inflect.engine()

type_to_folder = {name: _inflect.plural(name) for name, _value in ItemType.__members__.items()}  # type: ignore


def item_type_to_folder(item_type: ItemType) -> str:
    return type_to_folder[item_type.name]


class Format(Enum):
    url = "url"
    html = "html"
    markdown = "markdown"
    plaintext = "plaintext"


@dataclass
class Item:
    """
    An item that we may operate on. Could be one of various types, and may be persisted on disk or
    as a database record.
    """

    type: ItemType
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    body: Optional[str] = None
    format: Optional[Format] = None
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    def update_modified_at(self):
        self.modified_at = datetime.now()

    def assert_body(self) -> None:
        if not self.body:
            raise ValueError(f"Expected body for item: {self}")

    def metadata(self) -> dict:
        """
        Metadata is all non-None fields except the body, in easy-to-serialize form.
        """
        item_dict = asdict(self)
        item_dict = {k: v for k, v in item_dict.items() if v is not None and k != "body"}

        # Keep enum values as strings for simplicity with serialization to YAML.
        for field in ["type", "format"]:
            if item_dict.get(field):
                item_dict[field] = item_dict[field].name

        return item_dict

    def body_text(self) -> str:
        return self.body or ""

    def unique_slug(self, taken_slugs: Set[str] = set()) -> str:
        """Return a unique slug for this item."""

        title = self.title or self.url or self.description or self.body or "untitled"
        slug = slugify(title, max_length=50, separator="_")
        if slug not in taken_slugs:
            return slug
        i = 1
        while True:
            new_slug = f"{slug}_{i}"
            if new_slug not in taken_slugs:
                return new_slug
            i += 1

    def copy_with(self, **kwargs) -> "Item":
        """Copy item with the given field updates."""

        new_item = replace(self, **kwargs)
        new_item.created_at = datetime.now()
        new_item.modified_at = datetime.now()
        return new_item
