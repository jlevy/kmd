import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from strif import atomic_output_file


def render_template(template_file: str, output_path: str, data: dict, autoescape: bool = True):
    """
    Render a Jinja2 template file with the given data and write the output to a file.
    """
    # Load the Jinja2 environment.
    parent_dir = Path(os.path.abspath(os.path.dirname(__file__)))
    templates_dir = parent_dir / "templates"
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=autoescape)

    # Load and render the template.
    template = env.get_template(template_file)
    rendered_html = template.render(data)

    with atomic_output_file(output_path) as temp_file:
        with open(temp_file, "w") as file:
            file.write(rendered_html)
