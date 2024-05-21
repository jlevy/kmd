from os.path import join

from kmd.file_storage.workspaces import current_workspace
from kmd.actions.action_registry import register_action
from kmd.actions.action_registry import register_action
from kmd.model.actions_model import ONE_OR_MORE_ARGS, ONE_ARG, Action, ActionInput, ActionResult
from kmd.model.items_model import FileExt, Format, Item, ItemType
from kmd.pdf.pdf_output import markdown_to_pdf
from kmd.config.logger import get_logger
from kmd.web_gen.tabbed_web_page import configure_web_page, generate_web_page

log = get_logger(__name__)


@register_action
class ConfigureWebPage(Action):
    def __init__(self):
        super().__init__(
            name="configure_web_page",
            friendly_name="Configure a Web Page",
            description="Set up a web page config with tabs for each page of content. Uses first item as the page title.",
            expected_args=ONE_OR_MORE_ARGS,
        )

    def run(self, items: ActionInput) -> ActionResult:
        for item in items:
            if not item.body:
                raise ValueError(f"Item must have a body: {item}")

        # Determine item title etc from first item.
        first_item = items[0]
        title = first_item.get_title()
        config_item = configure_web_page(title, items)
        current_workspace().save(config_item)

        return ActionResult([config_item])


@register_action
class GenerateWebPage(Action):
    def __init__(self):
        super().__init__(
            name="generate_web_page",
            friendly_name="Generate Web Page",
            description="Generate a web page from a configured web page item.",
            expected_args=ONE_ARG,
        )

    def run(self, items: ActionInput) -> ActionResult:
        config_item = items[0]
        html = generate_web_page(config_item)

        web_page_item = Item(
            title=config_item.title,
            type=ItemType.export,
            format=Format.html,
            file_ext=FileExt.html,
            body=html,
        )

        return ActionResult([web_page_item])


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
