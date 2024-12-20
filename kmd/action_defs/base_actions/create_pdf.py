from os.path import join

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.lang_tools.clean_headings import clean_heading
from kmd.media.pdf_output import html_to_pdf
from kmd.model import (
    Action,
    ActionInput,
    ActionResult,
    ArgCount,
    FileExt,
    Format,
    ItemType,
    ONE_ARG,
    Precondition,
)
from kmd.model.args_model import fmt_loc
from kmd.preconditions.precondition_defs import has_html_body, has_text_body
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


@kmd_action
class CreatePDF(Action):

    name: str = "create_pdf"

    description: str = """
        Create a PDF from text or Markdown.
        """

    expected_args: ArgCount = ONE_ARG

    precondition: Precondition = has_text_body | has_html_body

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        if not item.body:
            raise InvalidInput(f"Item must have a body: {item}")

        pdf_item = item.derived_copy(type=ItemType.export, format=Format.pdf, file_ext=FileExt.pdf)
        pdf_path, _found, _old_pdf_path = current_workspace().store_path_for(pdf_item)
        log.message("Will save PDF to: %s", fmt_loc(pdf_path))
        base_dir = current_workspace().base_dir
        full_pdf_path = join(base_dir, pdf_path)

        clean_title = clean_heading(item.abbrev_title())

        # Convert to HTML if necessary.
        if item.format == Format.html:
            content_html = f"""
                <h1>{clean_title}</h1>
                {item.body_text()}
                """
        else:
            content_html = f"""
                <h1>{clean_title}</h1>
                {item.body_as_html()}
                """

        # Add directly to the store.
        html_to_pdf(
            content_html,
            full_pdf_path,
            title=item.title,
        )
        pdf_item.external_path = full_pdf_path

        return ActionResult([pdf_item])
