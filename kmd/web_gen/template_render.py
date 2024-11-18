import os
from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader

from kmd.config import colors


def render_web_template(
    template_file: str,
    data: dict,
    autoescape: bool = True,
    css_overrides: Dict[str, str] = {},
) -> str:
    """
    Render a Jinja2 template file with the given data, returning an HTML string.
    """
    # Load the Jinja2 environment.
    parent_dir = Path(os.path.abspath(os.path.dirname(__file__)))
    templates_dir = parent_dir / "templates"
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=autoescape)

    # Load and render the template.
    template = env.get_template(template_file)

    data = {**data, "color_defs": colors.generate_css_vars(css_overrides)}

    rendered_html = template.render(data)
    return rendered_html
