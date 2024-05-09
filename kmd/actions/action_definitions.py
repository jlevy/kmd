from dataclasses import dataclass
import logging
from os.path import join
from textwrap import dedent

from kmd.actions.llm_actions import LLM, LLMAction
from kmd.actions.registry import register_action, register_llm_action
from kmd.actions.registry import register_action
from kmd.file_storage.file_store import workspace
from kmd.media import web
from kmd.media.video import video_transcription
from kmd.model.actions_model import Action, ActionInput, ActionResult
from kmd.model.items_model import Format, Item, ItemType
from kmd.pdf.pdf_output import markdown_to_pdf

log = logging.getLogger(__name__)


@register_action
class FetchPageAction(Action):
    def __init__(self):
        super().__init__(
            name="fetch_page",
            friendly_name="Fetch Page Details",
            description="Fetches the title, description, and body of a web page.",
        )

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


@register_action
class TranscribeVideoAction(Action):
    def __init__(self):
        super().__init__(
            name="transcribe_video",
            friendly_name="Transcribe Video",
            description="Download and transcribe audio from a video.",
        )

    def run(self, items: ActionInput) -> ActionResult:
        item = items[0]
        url = item.url
        if not url:
            raise ValueError("Item must have a URL")

        transcription = video_transcription(url)

        item = Item(ItemType.note, body=transcription, format=Format.plaintext)
        workspace.save(item)

        return [item]


@register_action
class CreatePDFAction(Action):
    def __init__(self):
        super().__init__(
            name="create_pdf",
            friendly_name="Create PDF",
            description="Create a PDF from text or Markdown.",
        )

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


register_llm_action(
    name="proofread",
    friendly_name="Proofread and Correct",
    description="Proofread text, only fixing spelling, punctuation, and grammar.",
    model=LLM.gpt_3_5_turbo_16k_0613.value,
    system_message=dedent(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    title_template="{title} (proofread)",
    template=dedent(
        """
        Proofread the following text according to these rules:
        - Correct only typos or spelling, grammar, capitalization, or punctuation mistakes,
        - Write out only the final corrected text.
        - If input is a single phrase that looks like a question, be sure to add a question mark at the end.
        - Do not alter the meaning of any of the text or change the style of writing.
        - Do not capitalize words unless they are proper nouns or at the start of a sentence.
        - If unsure about any correction, leave that portion of the text unchanged.
        - Preserve all Markdown formatting.
        
        Input text:
        
        {body}

        Corrected text:
        """
    ),
)


register_llm_action(
    name="break_into_paragraphs",
    friendly_name="Reformat Text as Paragraphs",
    description="Reformat text as paragraphs.",
    model=LLM.gpt_3_5_turbo_16k_0613.value,
    system_message=dedent(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    title_template="{title} (in paragraphs)",
    template=dedent(
        """
        Format this text according to these rules:
        - Break the following text into paragraphs so it is readable and organized.
        - Add oriented quotation marks so quotes are “like this” and not "like this".
        - Make any other punctuation changes to fit the Chicago Manual of Style.
        - Do *not* change any words of the text. Add line breaks and punctuation and formatting changes only.
        - Preserve all Markdown formatting.

        Input text:

        {body}

        Formatted text:
        """
    ),
)

register_llm_action(
    name="summarize_as_bullets",
    friendly_name="Summarize as Bullet Points",
    description="Summarize text as bullet points.",
    model=LLM.gpt_3_5_turbo_16k_0613.value,
    system_message=dedent(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    title_template="Summary of {title}",
    template=dedent(
        """
        Summarize the following text as a list of concise bullet points, each one or two sentences long.
        Include all key numbers or facts, without omitting any key details.
        Use simple and precise language.
        It is very important you do not add any details that are not directly stated in the original text.
        Do not change any numbers or alter its meaning in any way.

        Input text:

        {body}

        Bullet points:
        """
    ),
)

register_llm_action(
    name="extract_concepts",
    friendly_name="Extract Concepts",
    description="Extract key concepts from text.",
    model=LLM.gpt_3_5_turbo_16k_0613.value,
    system_message=dedent(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    title_template="Concepts from {title}",
    template=dedent(
        """
        You are collecting concepts for the glossary of a book.
        Identify and list any concepts from the following text
        Only include unusual or technical terms or names of companies or people.
        Do not include common concepts or general ideas.
        Each concept should be a single word or noun phrase.
        Write them as an itemized list of bullet points in Markdown format, with each word or
        phrase in Title Case.

        Input text:

        {body}

        Concepts:
        """
    ),
)
