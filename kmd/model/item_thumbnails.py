from typing import Optional
from kmd.media.video_youtube import best_thumbnail
from kmd.model.items_model import Item
from kmd.util.url import Url


def item_thumbnail_image(item: Item) -> Optional[Url]:
    if item.thumbnail_url:
        return item.thumbnail_url

    # If we have extra data pointing to thumbnail.
    if item.extra and "youtube_metadata" in item.extra:
        return best_thumbnail(item.extra["youtube_metadata"])
