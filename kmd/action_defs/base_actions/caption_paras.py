from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.exec.llm_transforms import llm_transform_str
from kmd.model import (
    ANNOTATED_PARA,
    Format,
    Item,
    ItemType,
    LLMAction,
    Message,
    MessageTemplate,
    PARA,
    PARA_CAPTION,
)
from kmd.text_chunks.div_elements import div
from kmd.text_docs.sizes import TextUnit
from kmd.text_docs.text_doc import Paragraph, TextDoc
from kmd.util.task_stack import task_stack


log = get_logger(__name__)


@kmd_action
class CaptionParas(LLMAction):

    name: str = "caption_paras"

    description: str = """
        Caption each paragraph in the text with a very short summary.
        """

    system_message: Message = Message(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    )

    template: MessageTemplate = MessageTemplate(
        """
        You are a careful and precise editor. You are asked to describe what is said in the following
        one or two paragraphs, as a sort of summary or caption for the content. Rules:

        - Mention only the most important points. Include all the key topics discussed.
        
        - Keep the caption short! Use one or two short, complete sentences. It must be significantly
            shorter than the input text.
        
        - Write in clean and and direct language.

        - Do not mention the text or the author. Simply state the points as presented.

        - If the content contains other promotional material or only references information such as
            about what will be discussed later, ignore it.

        - DO NOT INCLUDE any other commentary.

        - If the input is very short or so unclear you can't summarize it, simply output
            "(No results)".

        Sample input text:

        I think push ups are one of the most underrated exercises out there and they're also one of
        the exercises that is most frequently performed with poor technique.
        And I think this is because a lot of people think it's just an easy exercise and they adopt
        a form that allows them to achieve a rep count that they would expect from an easy exercise,
        but all that ends up happening is they they do a bunch of poor quality repetitions in order
        to get a high rep count. So I don't think push ups are particularly easy when they're done well
        and they're really effective for building just general fitness and muscle in the upper body
        if you do them properly. So here's how you get the most out of them.

        Sample output text:

        Push ups are an underrated exercise. They are not easy to do well so are often done poorly.

        Input text:

        {body}

        Output text:
        """
    )

    def run_item(self, item: Item) -> Item:

        if not item.body:
            raise InvalidInput(f"LLM actions expect a body: {self.name} on {item}")

        doc = TextDoc.from_text(item.body)
        output = []
        with task_stack().context(self.name, doc.size(TextUnit.paragraphs), "para") as ts:
            for para in doc.paragraphs:
                if para.size(TextUnit.words) > 0:
                    output.append(self.process_para(para))
                ts.next()

        final_output = "\n\n".join(output)

        result_item = item.derived_copy(type=ItemType.doc, body=final_output, format=Format.md_html)

        return result_item

    def process_para(self, para: Paragraph) -> str:
        caption_div = None

        para_str = para.reassemble()
        # Only caption actual paragraphs with enough words.
        if not para.is_markup() and not para.is_header() and para.size(TextUnit.words) > 40:
            llm_response = llm_transform_str(self.context(), para_str)
            caption_div = div(PARA_CAPTION, llm_response)
            new_div = div(ANNOTATED_PARA, caption_div, div(PARA, para_str))
        else:
            new_div = para_str
        return new_div
