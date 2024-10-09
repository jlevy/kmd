from os.path import join

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.file_storage.workspaces import current_workspace
from kmd.lang_tools.clean_headings import clean_heading
from kmd.media.pdf_output import html_to_pdf
from kmd.model import Action, ActionInput, ActionResult, FileExt, Format, ItemType, ONE_ARG
from kmd.preconditions.precondition_defs import has_text_body

log = get_logger(__name__)


@kmd_action
class CreatePDF(Action):
    def __init__(self):
        super().__init__(
            name="create_pdf",
            description="Create a PDF from text or Markdown.",
            expected_args=ONE_ARG,
            precondition=has_text_body,
        )

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        if not item.body:
            raise InvalidInput(f"Item must have a body: {item}")

        pdf_item = item.derived_copy(type=ItemType.export, format=Format.pdf, file_ext=FileExt.pdf)
        pdf_path, _old_pdf_path = current_workspace().find_path_for(pdf_item)
        base_dir = current_workspace().base_dir
        full_pdf_path = join(base_dir, pdf_path)

        clean_title = clean_heading(item.abbrev_title())

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
