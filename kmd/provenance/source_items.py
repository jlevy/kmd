from kmd.config.logger import get_logger
from kmd.errors import NoMatch
from kmd.file_storage.workspaces import current_workspace
from kmd.model.items_model import Item
from kmd.model.paths_model import StorePath
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_defs import is_resource
from kmd.util.format_utils import fmt_lines, fmt_path
from kmd.util.type_utils import not_none

log = get_logger(__name__)


def find_upstream_item(item: Item, precondition: Precondition, include_self: bool = True) -> Item:
    """
    Breadth-first search up the `derived_from` provenance tree to find the first item that
    the validator accepts. Validator should throw `PreconditionFailure`.
    """

    if include_self and precondition(item):
        return item

    if not item.relations.derived_from:
        raise NoMatch(f"Item must be derived from another item: {item}")

    workspace = current_workspace()

    source_items = [workspace.load(StorePath(loc)) for loc in item.relations.derived_from]

    for source_item in source_items:
        if precondition(source_item):
            log.message(
                "Found source item that matches requirements:\n%s",
                fmt_lines([fmt_path(not_none(source_item.store_path))]),
            )
            return source_item
        else:
            log.message(
                "Skipping source item that does not match requirements: %s",
                source_item.store_path,
            )

    for source_item in source_items:
        try:
            return find_upstream_item(source_item, precondition)
        except NoMatch:
            pass

    raise NoMatch(f"Could not find a source item that fits the precondition: {item}")


def find_upstream_resource(item: Item) -> Item:
    return find_upstream_item(item, is_resource)
