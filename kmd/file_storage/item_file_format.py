from datetime import datetime, timezone
from pathlib import Path

from frontmatter_format import fmf_read, fmf_write, FmStyle

from kmd.config.logger import get_logger
from kmd.errors import FileFormatError
from kmd.file_storage.file_cache import FileMtimeCache
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ITEM_FIELDS
from kmd.model.operations_model import OPERATION_FIELDS
from kmd.text_formatting.doc_formatting import normalize_formatting
from kmd.util.format_utils import fmt_path
from kmd.util.log_calls import tally_calls
from kmd.util.sort_utils import custom_key_sort

log = get_logger(__name__)

# Keeps YAML much prettier.
ITEM_FIELD_SORT = custom_key_sort(OPERATION_FIELDS + ITEM_FIELDS)

# Initialize the file modification time cache with Item type
_item_cache = FileMtimeCache[Item](max_size=2000)


@tally_calls()
def write_item(item: Item, full_path: Path):
    if item.is_binary:
        raise ValueError(f"Binary Items should be external files: {item}")

    # Clear cache before writing.
    _item_cache.delete(full_path)

    body = normalize_formatting(item.body_text(), item.format)

    # Special case for YAML files
    if body and item.format == Format.yaml:
        stripped = body.lstrip()
        if stripped.startswith("---\n"):
            body = stripped[4:]

    # Detect the frontmatter style
    if str(item.format) == str(Format.html):
        fm_style = FmStyle.html
    elif str(item.format) in [str(Format.python), str(Format.csv)]:
        fm_style = FmStyle.hash
    else:
        fm_style = FmStyle.yaml

    log.debug(
        "Writing item to %s: body length %s, metadata %s", full_path, len(body), item.metadata()
    )
    fmf_write(
        full_path,
        body,
        item.metadata(),
        style=fm_style,
        key_sort=ITEM_FIELD_SORT,
        make_parents=True,
    )

    # Update cache.
    _item_cache.update(full_path, item)


def read_item(full_path: Path, base_dir: Path) -> Item:
    cached_item = _item_cache.read(full_path)
    if cached_item is not None:
        log.debug("Cache hit for %s", full_path)
        return cached_item

    return read_item_uncached(full_path, base_dir)


@tally_calls()
def read_item_uncached(full_path: Path, base_dir: Path) -> Item:
    body, metadata = fmf_read(full_path)
    log.debug("Read item from %s: body length %s, metadata %s", full_path, len(body), metadata)
    if not metadata:
        raise FileFormatError(f"No metadata found in file: {fmt_path(full_path)}")

    try:
        store_path = str(full_path.relative_to(base_dir))
        external_path = None
    except ValueError:
        store_path = None
        external_path = str(full_path)
    item = Item.from_dict(metadata, body=body, store_path=store_path, external_path=external_path)
    # Update modified time from the file system.
    item.modified_at = datetime.fromtimestamp(full_path.stat().st_mtime, tz=timezone.utc)

    # Update the cache with the new item
    _item_cache.update(full_path, item)

    return item
