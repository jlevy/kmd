from dataclasses import dataclass
from os.path import join
from typing import List
from kmd.file_storage.file_store import workspace
from kmd.media import web
from kmd.model.model import Action, Format, Item
from kmd.pdf import pdf_output


# For now these are simple but we may want to support other hints or output data in the future.
ActionInput = List[Item]
ActionResult = List[Item]


@dataclass
class CrawlAction(Action):
    name = "Fetch Page Details"
    description = "Fetches the title, description, and body of a web page."

    def __init__(self):
        super().__init__(name=self.name, description=self.description)

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        if not item.url:
            raise ValueError("Item must have a URL")
        page_data = web.fetch_extract(item.url)
        item.title = page_data.title
        item.description = page_data.description
        item.body = page_data.content

        # TODO: Archive old item, indicate this replaces it.
        return [item]


@dataclass
class CreatePDFAction(Action):
    name = "Create PDF"
    description = "Create a PDF from text or Markdown."

    def __init__(self):
        super().__init__(name=self.name, description=self.description)

    def run(self, items: ActionInput) -> ActionResult:
        # TODO: Support concatenating multiple items into a single PDF (have to handle titles sensibly).
        item = items[0]
        if not item.body:
            raise ValueError("Item must have a body")

        pdf_item = item.copy_with(format=Format.pdf)
        base_dir, pdf_path = workspace.path_for(pdf_item)
        full_pdf_path = join(base_dir, pdf_path)

        pdf_output.markdown_to_pdf(
            item.body,
            full_pdf_path,
            title=item.title,
            description=item.description,
        )

        pdf_item.external_path = full_pdf_path
        workspace.save(pdf_item)
        return [pdf_item]
