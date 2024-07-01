from typing import Optional
from kmd.media.video_youtube import best_thumbnail
from kmd.model.items_model import Item
from kmd.util.url import Url


def item_thumbnail_image(item: Item) -> Optional[Url]:
    # For now just showing YouTube thumbnails but should expand this to more kinds of media/URLs.
    if item.extra and "youtube_metadata" in item.extra:
        return best_thumbnail(item.extra["youtube_metadata"])
