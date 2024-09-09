from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, Optional, Set

from strif import abbreviate_list

from kmd.config.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    title: str
    description: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None


@dataclass(frozen=True)
class Link:
    source: str
    target: str
    relationship: str
    distance: Optional[float] = None


@dataclass
class GraphData:
    nodes: Dict[str, Node] = field(default_factory=dict)
    # We allow duplicate links as long as they are of different relationships.
    links: Set[Link] = field(default_factory=set)

    def __init__(
        self, nodes: Optional[Iterable[Node]] = None, links: Optional[Iterable[Link]] = None
    ):
        self.nodes = {node.id: node for node in nodes} if nodes else {}
        self.links = set(links) if links else set()

    def merge(self, nodes: Iterable[Node], links: Iterable[Link]):
        """
        Merge new nodes and links into the existing graph.
        """
        for node in nodes:
            self.nodes[node.id] = node
        self.links.update(links)

    def prune(self) -> "GraphData":
        """
        Ensure the graph is valid by pruning edges to nonexistent nodes.
        Returns the new graph.
        """
        valid_links = set()
        missing_ids = set()

        for link in self.links:
            if link.source in self.nodes and link.target in self.nodes:
                valid_links.add(link)
            else:
                if link.source not in self.nodes:
                    missing_ids.add(link.source)
                if link.target not in self.nodes:
                    missing_ids.add(link.target)

        if len(valid_links) != len(self.links):
            log.warning(
                "In graph view, removed %d links to orphaned nodes: %s",
                len(self.links) - len(valid_links),
                abbreviate_list(list(missing_ids)),
            )

        return GraphData(nodes=self.nodes.values(), links=valid_links)

    def remove_node(self, node_id: str):
        """
        Remove a node and all its associated links from the graph.
        """
        self.nodes.pop(node_id, None)
        self.links = {
            link for link in self.links if link.source != node_id and link.target != node_id
        }

    def to_serializable(self) -> dict:
        """
        Convert the graph to D3 JSON-compatible format.
        """
        return {
            "nodes": [asdict(node) for node in self.nodes.values()],
            "links": [asdict(link) for link in self.links],
        }
