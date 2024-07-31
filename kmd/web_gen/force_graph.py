from kmd.config.logger import get_logger
from kmd.model.graph_model import GraphData
from kmd.web_gen.template_render import render_web_template

log = get_logger(__name__)


def force_graph_generate(title: str, graph: GraphData) -> str:
    content = render_web_template("force_graph.template.html", {"graph": graph.to_serializable()})
    return render_web_template("base_webpage.template.html", {"title": title, "content": content})
