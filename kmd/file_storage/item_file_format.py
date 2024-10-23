from pathlib import Path
from typing import Optional

from kmd.config.logger import get_logger
from kmd.errors import FileFormatError
from kmd.file_formats.frontmatter_format import fmf_read, fmf_write, FmStyle
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ITEM_FIELDS
from kmd.model.operations_model import OPERATION_FIELDS
from kmd.text_formatting.doc_formatting import normalize_formatting
from kmd.util.format_utils import fmt_path
from kmd.util.sort_utils import custom_key_sort

log = get_logger(__name__)


# Keeps YAML much prettier.
ITEM_FIELD_SORT = custom_key_sort(OPERATION_FIELDS + ITEM_FIELDS)


def write_item(item: Item, full_path: Path):
    if item.is_binary:
        raise ValueError(f"Binary Items should be external files: {item}")

    body = normalize_formatting(item.body_text(), item.format)

    # Special case of YAML files that already have a `---`, which is not
    # necessary since we'll write it ourselves.
    if body and item.format == Format.yaml:
        stripped = body.lstrip()
        if stripped.startswith("---\n"):
            body = stripped[4:]

    # Detect what style of frontmatter to use so it's compatible with the content.
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


def read_item(full_path: Path, base_dir: Optional[Path]) -> Item:
    store_path = str(full_path.relative_to(base_dir)) if base_dir else None
    body, metadata = fmf_read(full_path)
    log.debug("Read item from %s: body length %s, metadata %s", full_path, len(body), metadata)
    if not metadata:
        raise FileFormatError(f"No metadata found in file: {fmt_path(full_path)}")

    return Item.from_dict(metadata, body=body, store_path=store_path)
