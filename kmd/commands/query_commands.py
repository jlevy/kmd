from typing import cast

from frontmatter_format import to_yaml_string

from kmd.commands.command_registry import kmd_command
from kmd.exec.resolve_args import assemble_store_path_args
from kmd.shell_ui.shell_output import cprint, print_response, print_status, Wrap
from kmd.util.format_utils import fmt_lines
from kmd.workspaces.workspaces import current_workspace


@kmd_command
def index(*paths: str) -> None:
    """
    Index the items at the given path, or the current selection.
    """
    store_paths = assemble_store_path_args(*paths)
    ws = current_workspace()

    ws.vector_index.index_items([ws.load(store_path) for store_path in store_paths])

    print_status(f"Indexed:\n{fmt_lines(store_paths)}")


@kmd_command
def unindex(*paths: str) -> None:
    """
    Unarchive the items at the given paths.
    """
    store_paths = assemble_store_path_args(*paths)
    ws = current_workspace()
    ws.vector_index.unindex_items([ws.load(store_path) for store_path in store_paths])

    print_status(f"Unindexed:\n{fmt_lines(store_paths)}")


def _output_scored_node(scored_node, show_metadata: bool = True):
    from llama_index.core.schema import TextNode

    node = cast(TextNode, scored_node.node)
    cprint()
    cprint(
        f"Score {scored_node.score}\n    {node.ref_doc_id}\n    node {node.node_id}",
        text_wrap=Wrap.NONE,
    )
    print_response("%s", node.text, text_wrap=Wrap.WRAP_INDENT)

    if show_metadata and node.metadata:
        cprint("%s", to_yaml_string(node.metadata), text_wrap=Wrap.INDENT_ONLY)


@kmd_command
def retrieve(query_str: str) -> None:
    """
    Retrieve matches from the index for the given string or query.
    """

    ws = current_workspace()
    results = ws.vector_index.retrieve(query_str)

    cprint()
    cprint(f"Matches from {ws.vector_index}:")
    for scored_node in results:
        _output_scored_node(scored_node)


@kmd_command
def query(query_str: str) -> None:
    """
    Query the index for an answer to the given question.
    """
    from llama_index.core.base.response.schema import Response

    ws = current_workspace()
    results = cast(Response, ws.vector_index.query(query_str))

    cprint()
    cprint(f"Response from {ws.vector_index}:", text_wrap=Wrap.NONE)
    print_response("%s", results.response, text_wrap=Wrap.WRAP_FULL)

    if results.source_nodes:
        cprint("Sources:")
        for scored_node in results.source_nodes:
            _output_scored_node(scored_node)

    # if results.metadata:
    #     output("Metadata:")
    #     output("%s", to_yaml_string(results.metadata), text_wrap=Wrap.INDENT_ONLY)
