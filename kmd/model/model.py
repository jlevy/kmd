from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
import enum
from typing import Optional, Set

from slugify import slugify


@dataclass
class Action:
    name: str
    description: str
    model: str
    system_message: str
    template: str
    implementation: str = "builtin"


class ItemTypeEnum(enum.Enum):
    """Kinds of Items. Value is unique folder name, which is the plural of the item type."""

    note = "notes"
    question = "questions"
    concept = "concepts"
    answer = "answers"
    resource = "resources"
    description = "descriptions"


def item_type_to_folder(item_type: ItemTypeEnum) -> str:
    return item_type.value


def folder_to_item_type(folder: str) -> ItemTypeEnum:
    for item_type in ItemTypeEnum:
        if item_type.value == folder:
            return item_type
    raise ValueError(f"Unknown item type folder: {folder}")


class ResourceTypeEnum(enum.Enum):
    web_page = "web_page"
    url = "url"
    video = "video"
    audio = "audio"


@dataclass
class Item:
    """
    An item that we may operate on. Could be one of various types, and may be persisted on disk or
    as a database record.
    """

    type: ItemTypeEnum
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    body: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: Optional[datetime] = None

    def update_modified_at(self):
        self.modified_at = datetime.now()

    def assert_body(self) -> None:
        if not self.body:
            raise ValueError(f"Expected body for item: {self}")

    def metadata(self) -> dict:
        """Metadata is all non-None fields except the body."""
        item_dict = asdict(self)
        item_dict = {k: v for k, v in item_dict.items() if v is not None and k != "body"}
        # Keep type as a string.
        if item_dict.get("type"):
            item_dict["type"] = item_dict["type"].name
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


def copy_with(item: Item, **kwargs) -> Item:
    """Copy item with the given field updates."""

    new_item = replace(item, **kwargs)
    new_item.created_at = datetime.now()
    new_item.modified_at = datetime.now()
    return new_item
