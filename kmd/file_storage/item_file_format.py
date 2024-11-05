from pathlib import Path
from typing import Optional

from frontmatter_format import fmf_read, fmf_write, FmStyle

from kmd.config.logger import get_logger
from kmd.file_storage.file_cache import FileMtimeCache
from kmd.model.args_model import fmt_loc
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ITEM_FIELDS
from kmd.model.operations_model import OPERATION_FIELDS
from kmd.text_formatting.doc_formatting import normalize_formatting
from kmd.util.log_calls import tally_calls
from kmd.util.sort_utils import custom_key_sort

log = get_logger(__name__)

# Keeps YAML much prettier.
ITEM_FIELD_SORT = custom_key_sort(OPERATION_FIELDS + ITEM_FIELDS)

# Initialize the file modification time cache with Item type
_item_cache = FileMtimeCache[Item](max_size=2000)


@tally_calls()
def write_item(item: Item, path: Path):
    """
    Write a text item to a file with standard frontmatter format YAML.
    Also normalizes formatting of the body text.
    """
    item.validate()
    if item.is_binary:
        raise ValueError(f"Binary items should be external files: {item}")
    if item.format and not item.format.supports_frontmatter():
        raise ValueError(f"Item format `{item.format.value}` does not support frontmatter: {item}")

    # Clear cache before writing.
    _item_cache.delete(path)

    body = normalize_formatting(item.body_text(), item.format)

    # Special case for YAML files to avoid a possible duplicate `---` divider in the body.
    if body and item.format == Format.yaml:
        stripped = body.lstrip()
        if stripped.startswith("---\n"):
            body = stripped[4:]

    # Decide on the frontmatter style.
    format = Format(item.format)
    if format == Format.html:
        fm_style = FmStyle.html
    elif format in [Format.python, Format.kmd_script, Format.diff, Format.csv]:
        fm_style = FmStyle.hash
    elif format == Format.json:
        fm_style = FmStyle.slash
    else:
        fm_style = FmStyle.yaml

    log.debug("Writing item to %s: body length %s, metadata %s", path, len(body), item.metadata())

    fmf_write(
        path,
        body,
        item.metadata(),
        style=fm_style,
        key_sort=ITEM_FIELD_SORT,
        make_parents=True,
    )

    # Update cache.
    _item_cache.update(path, item)


def read_item(path: Path, base_dir: Optional[Path]) -> Item:
    """
    Read an item from a file. Uses `base_dir` to resolve paths, so the item's
    `store_path` will be set and be relative to `base_dir`.

    If frontmatter format YAML is present, it is parsed. If not, the item will
    be a resource with a format inferred from the file extension or the content,
    and the `external_path` will be set to the path it was read from.
    """

    cached_item = _item_cache.read(path)
    if cached_item:
        log.debug("Cache hit for item: %s", path)
        return cached_item

    return _read_item_uncached(path, base_dir)


@tally_calls()
def _read_item_uncached(path: Path, base_dir: Optional[Path]) -> Item:
    body, metadata = fmf_read(path)
    log.debug("Read item from %s: body length %s, metadata %s", path, len(body), metadata)

    path = path.resolve()
    if base_dir:
        base_dir = base_dir.resolve()

    # Ensure store_path is used if it's within the base_dir, and
    # external_path otherwise.
    if base_dir and path.is_relative_to(base_dir):
        store_path = str(path.relative_to(base_dir))
        external_path = None
    else:
        store_path = None
        external_path = str(path)

    if metadata:
        item = Item.from_dict(
            metadata, body=body, store_path=store_path, external_path=external_path
        )
    else:
        # No frontmatter, so infer from the file and content.
        item = Item.from_external_path(path)
        if item.format and item.format.supports_frontmatter():
            log.info(
                "Metadata not present on text file, inferred format `%s`: %s",
                item.format.value,
                fmt_loc(path),
            )
        item.store_path = store_path
        item.external_path = external_path
        item.body = body

    # Update modified time.
    item.set_modified(path.stat().st_mtime)

    # Update the cache with the new item
    _item_cache.update(path, item)

    return item
