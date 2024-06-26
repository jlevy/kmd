from kmd.file_storage.workspaces import current_workspace
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item
from kmd.config.logger import get_logger
from kmd.model.locators import StorePath
from kmd.preconditions.precondition import Precondition

log = get_logger(__name__)


def find_upstream_item(item: Item, precondition: Precondition) -> Item:
    """
    Breadth-first search up the `derived_from` provenance tree to find the first item that
    the validator accepts. Validator should throw `PreconditionFailure`.
    """

    workspace = current_workspace()

    if not item.relations.derived_from:
        raise InvalidInput(f"Item must be derived from another item: {item}")

    source_items = [workspace.load(StorePath(loc)) for loc in item.relations.derived_from]

    for source_item in source_items:
        if precondition(source_item):
            log.message("Found source item that matches requirements: %s", source_item.store_path)
            return source_item
        else:
            log.message(
                "Skipping source item that does not match requirements: %s: %s",
                source_item.store_path,
            )

    for source_item in source_items:
        try:
            return find_upstream_item(source_item, precondition)
        except InvalidInput:
            pass

    raise InvalidInput(f"Could not find a source item that passes the validator: {item}")
