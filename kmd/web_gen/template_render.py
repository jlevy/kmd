import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from kmd.config import colors


def render_web_template(template_file: str, data: dict, autoescape: bool = True) -> str:
    """
    Render a Jinja2 template file with the given data, returning an HTML string.
    """
    # Load the Jinja2 environment.
    parent_dir = Path(os.path.abspath(os.path.dirname(__file__)))
    templates_dir = parent_dir / "templates"
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=autoescape)

    # Load and render the template.
    template = env.get_template(template_file)

    # Include other useful variables like colors.
    additional_vars = {
        "colors": {name: value for name, value in vars(colors).items() if not name.startswith("__")}
    }

    rendered_html = template.render(data, **additional_vars)
    return rendered_html
