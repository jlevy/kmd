from kmd.commands.command_registry import kmd_command
from kmd.config.logger import get_logger
from kmd.model.items_model import ItemType
from kmd.viz.graph_view import assemble_workspace_graph, open_graph_view

log = get_logger(__name__)


@kmd_command
def graph_view(
    docs_only: bool = False, concepts_only: bool = False, resources_only: bool = False
) -> None:
    """
    Open a graph view of the current workspace.

    :param concepts_only: Show only concepts.
    :param resources_only: Show only resources.
    """
    if docs_only:
        item_filter = lambda item: item.type == ItemType.doc
    elif concepts_only:
        item_filter = lambda item: item.type == ItemType.concept
    elif resources_only:
        item_filter = lambda item: item.type == ItemType.resource
    else:
        item_filter = None
    open_graph_view(assemble_workspace_graph(item_filter))


# TODO:
# def define_action_sequence(name: str, *action_names: str):
#     action_registry.define_action_sequence(name, *action_names)
#     log.message("Registered action sequence: %s of actions: %s", name, action_names)
