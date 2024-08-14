from pathlib import Path
from kmd.shell_tools.native_tools import show_file_platform_specific
from kmd.config.logger import get_logger
from kmd.model.graph_model import GraphData, Node, Link
from kmd.web_gen.force_graph import force_graph_generate
from kmd.file_storage.workspaces import current_workspace, current_workspace_tmp_dir

log = get_logger(__name__)


def generate_graph_view_html(data: GraphData) -> Path:
    html = force_graph_generate("Knowledge Graph", data)

    html_path = current_workspace_tmp_dir() / "graph_view.html"
    with open(html_path, "w") as f:
        f.write(html)

    return html_path


def assemble_workspace_graph() -> GraphData:
    """
    Get the graph for the entire current workspace.
    """
    ws = current_workspace()

    graph_data = GraphData()

    for store_path in ws.walk_items():
        try:
            item = ws.load(store_path)
            node, links = item.as_node_links()
            graph_data.merge([node], links)
        except Exception as e:
            log.warning("Error processing item: %s: %s", store_path, e, exc_info=e)

    return graph_data.validate()


def open_graph_view(graph: GraphData):
    html_path = generate_graph_view_html(graph)
    show_file_platform_specific(html_path)


## Tests

test_data = GraphData(
    nodes=[
        Node(
            id="concepts/concept_a.md",
            type="concept",
            title="Concept A",
            body="This is a description of Concept A.",
        ),
        Node(
            id="notes/note_b.md",
            type="note",
            title="Note B",
            body="This is a note related to Concept A.",
            url="http://example.com/noteB",
        ),
        Node(
            id="concepts/concept_c.md",
            type="concept",
            title="Concept C",
            body="This is a description of Concept C.",
            url="http://example.com/conceptC",
        ),
        Node(
            id="resources/resource_d.md",
            type="resource",
            title="Resource D",
            body="This is a description of Resource D.",
            url="http://example.com/resourceD",
        ),
    ],
    links=[
        Link(source="concepts/concept_a.md", target="notes/note_b.md", relationship="related to"),
        Link(
            source="concepts/concept_a.md",
            target="concepts/concept_c.md",
            relationship="related to",
        ),
        Link(source="notes/note_b.md", target="concepts/concept_c.md", relationship="references"),
        Link(
            source="notes/note_b.md",
            target="resources/resource_d.md",
            relationship="references",
        ),
    ],
)

if __name__ == "__main__":
    open_graph_view(test_data)
