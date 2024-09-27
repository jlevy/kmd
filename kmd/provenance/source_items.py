from typing import Optional, Set

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


def find_upstream_item(
    item: Item,
    precondition: Precondition,
    include_self: bool = True,
    visited: Optional[Set[StorePath]] = None,
) -> Item:
    """
    Breadth-first search up the `derived_from` provenance tree to find the first item that
    matches the precondition.
    """
    if not item.store_path:
        raise ValueError("Cannot trace provenance without a store path")
    store_path = StorePath(item.store_path)

    # Circular dependencies generally shouldn't happen but let's avoid them to be safe.
    if visited is None:
        visited = set()
    if store_path in visited:
        log.warning(
            "Detected a loop searching for upstream item with precondition `%s` at %s. Aborting this path.",
            precondition,
            fmt_path(store_path),
        )
        raise NoMatch("Loop detected")

    visited.add(store_path)

    if include_self and precondition(item):
        return item

    if not item.relations.derived_from:
        raise NoMatch(f"Item must be derived from another item: {item}")

    workspace = current_workspace()

    source_items = [workspace.load(StorePath(loc)) for loc in item.relations.derived_from]

    for source_item in source_items:
        source_path = not_none(source_item.store_path)
        if precondition(source_item):
            log.message(
                "Found source item that matches requirements:\n%s",
                fmt_lines([fmt_path(source_path)]),
            )
            return source_item
        else:
            log.message(
                "Skipping source item that does not match precondition `%s`:\n%s",
                precondition,
                fmt_lines([fmt_path(source_path)]),
            )

    for source_item in source_items:
        try:
            return find_upstream_item(source_item, precondition, visited=visited)
        except NoMatch:
            pass

    raise NoMatch(
        f"Could not find a source item that fits the precondition {precondition}: {store_path}"
    )


def find_upstream_resource(item: Item) -> Item:
    return find_upstream_item(item, is_resource)
