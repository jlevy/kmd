from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from marko import Markdown
from typing import Optional
from pathlib import Path


def markdown_to_pdf(
    markdown_text: str,
    output_file_path: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> None:
    """
    Converts a Markdown string to a nicely formatted PDF file, with optional title, description, and footer.
    """

    # Setup Jinja2 environment.
    env = Environment(loader=FileSystemLoader(Path(__file__).parent))
    template = env.get_template("pdf_template.html")

    # Convert Markdown to HTML.
    markdown_parser = Markdown()
    html_content = markdown_parser.convert(markdown_text)

    # Render the template with variables.
    # TODO: Add more citations/sources from the item on the last page.
    rendered_html = template.render(
        title=title,
        subtitle=description,
        body_content=html_content,
        date=datetime.now().strftime("%Y-%m-%d"),
    )

    # Create PDF.
    weasy_html = HTML(string=rendered_html)
    weasy_html.write_pdf(output_file_path)
