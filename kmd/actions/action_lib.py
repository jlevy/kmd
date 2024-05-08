from dataclasses import dataclass
import logging
from os.path import join
from typing import List
from kmd.file_storage.file_store import workspace
from kmd.media import web
from kmd.media.video import video_transcription
from kmd.model.model import Action, Format, Item, ItemType

from kmd.pdf.pdf_output import markdown_to_pdf

log = logging.getLogger(__name__)

# For now these are simple but we may want to support other hints or output data in the future.
ActionInput = List[Item]
ActionResult = List[Item]


@dataclass
class FetchPageAction(Action):
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
        workspace.save(item)

        return [item]


@dataclass
class TranscribeVideoAction(Action):
    name = "Transcribe Video"
    description = "Download and transcribe audio from a video."

    def __init__(self):
        super().__init__(name=self.name, description=self.description)

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        url = item.url
        if not url:
            raise ValueError("Item must have a URL")

        transcription = video_transcription(url)

        item = Item(ItemType.note, body=transcription, format=Format.plaintext)
        workspace.save(item)

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

        pdf_item = item.copy_with(type=ItemType.export, format=Format.pdf)
        base_dir, pdf_path = workspace.path_for(pdf_item)
        full_pdf_path = join(base_dir, pdf_path)

        # Add directly to the store.
        markdown_to_pdf(
            item.body,
            full_pdf_path,
            title=item.title,
            description=item.description,
        )
        pdf_item.external_path = full_pdf_path
        workspace.save(pdf_item)

        return [pdf_item]
