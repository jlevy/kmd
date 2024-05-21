from os.path import join
from kmd.file_storage.workspaces import current_workspace
from kmd.actions.action_registry import register_action
from kmd.actions.action_registry import register_action
from kmd.model.actions_model import ONE_ARG, Action, ActionInput, ActionResult
from kmd.model.items_model import FileExt, Format, ItemType
from kmd.pdf.pdf_output import markdown_to_pdf
from kmd.config.logger import get_logger

log = get_logger(__name__)


@register_action
class CreatePDF(Action):
    def __init__(self):
        super().__init__(
            name="create_pdf",
            friendly_name="Create PDF",
            description="Create a PDF from text or Markdown.",
            expected_args=ONE_ARG,
        )

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        if not item.body:
            raise ValueError(f"Item must have a body: {item}")

        pdf_item = item.new_copy_with(type=ItemType.export, format=Format.pdf, file_ext=FileExt.pdf)
        base_dir, pdf_path = current_workspace().find_path_for(pdf_item)
        full_pdf_path = join(base_dir, pdf_path)

        # Add directly to the store.
        markdown_to_pdf(
            item.body,
            full_pdf_path,
            title=item.title,
            description=item.description,
        )
        pdf_item.external_path = full_pdf_path
        current_workspace().save(pdf_item)

        return ActionResult([pdf_item])
