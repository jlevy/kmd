from pathlib import Path

from kmd.errors import InvalidInput
from kmd.file_storage.file_store import FileStore
from kmd.model.args_model import CommandArg
from kmd.model.canon_url import canonicalize_url
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType
from kmd.model.paths_model import StorePath
from kmd.util.url import is_url, Url
from kmd.workspaces.workspaces import log


def import_url_to_workspace(ws: FileStore, url: Url) -> Item:
    """
    Import a URL as a resource. Should call fetch_page to fill in metadata.
    """
    canon_url = canonicalize_url(url)
    log.message(
        "Importing URL: %s%s", canon_url, f" canonicalized from {url}" if url != canon_url else ""
    )
    item = Item(ItemType.resource, url=canon_url, format=Format.url)
    # No need to overwrite any resource we already have for the identical URL.
    store_path = ws.save(item, overwrite=False)
    # Load to fill in any metadata we may already have.
    item = ws.load(store_path)
    return item


def import_and_load(ws: FileStore, locator: CommandArg) -> Item:
    """
    Ensure that the URL or Item is saved to the workspace.
    """

    if isinstance(locator, str) and is_url(locator):
        log.message("Importing locator as URL: %r", locator)
        item = import_url_to_workspace(ws, Url(locator))
    else:
        if isinstance(locator, StorePath):
            log.info("Locator is in the file store: %r", locator)
            # It's already a StorePath.
            item = ws.load(locator)
        else:
            log.message("Importing locator as local path: %r", locator)
            path = Path(locator)
            if not path.exists():
                raise InvalidInput(f"File not found: {path}")

            store_path = ws.import_item(path)
            item = ws.load(store_path)

    return item
