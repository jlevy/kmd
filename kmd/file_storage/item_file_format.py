from pathlib import Path
from typing import Optional
from kmd.file_storage.yaml_util import custom_key_sort
from kmd.model.errors_model import FileFormatError
from kmd.model.file_formats_model import Format
from kmd.model.items_model import ITEM_FIELDS, Item
from kmd.file_storage.frontmatter_format import FmFormat, fmf_read, fmf_write
from kmd.model.operations_model import OPERATION_FIELDS
from kmd.text_formatting.doc_formatting import normalize_formatting
from kmd.config.logger import get_logger

log = get_logger(__name__)


# Keeps YAML much prettier.
ITEM_FIELD_SORT = custom_key_sort(OPERATION_FIELDS + ITEM_FIELDS)


def write_item(item: Item, full_path: Path):
    if item.is_binary:
        raise ValueError(f"Binary Items should be external files: {item}")

    formatted_body = normalize_formatting(item.body_text(), item.format)

    if str(item.format) == str(Format.html):
        fmformat = FmFormat.html
    elif str(item.format) == str(Format.python):
        fmformat = FmFormat.code
    else:
        fmformat = FmFormat.yaml

    fmf_write(
        full_path,
        formatted_body,
        item.metadata(),
        format=fmformat,
        key_sort=ITEM_FIELD_SORT,
    )


def read_item(full_path: Path, base_dir: Optional[Path]) -> Item:
    # This is a known text format or a YAML file, so we can read the whole thing.
    store_path = str(full_path.relative_to(base_dir)) if base_dir else None
    body, metadata = fmf_read(full_path)
    if not metadata:
        raise FileFormatError(
            f"No metadata found in file: {store_path if store_path else full_path}"
        )

    return Item.from_dict(metadata, body=body, store_path=store_path)
