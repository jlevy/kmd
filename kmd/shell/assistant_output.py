from rich.text import Text

from kmd.config.text_styles import COLOR_HEADING, COLOR_HINT, COLOR_STATUS, EMOJI_ASSISTANT
from kmd.model.assistant_response_model import AssistantResponse, Confidence
from kmd.model.language_models import LLM
from kmd.shell.shell_output import (
    cprint,
    print_assistance,
    print_code_block,
    print_small_heading,
    print_style,
    print_text_block,
    Style,
    Wrap,
)
from kmd.text_formatting.markdown_normalization import fill_markdown


def print_assistant_heading(model: LLM) -> None:
    assistant_name = Text(f"{EMOJI_ASSISTANT} Kmd Assistant", style=COLOR_HEADING)
    info = Text(f"({model})", style=COLOR_HINT)
    cprint(assistant_name + " " + info)


def print_assistant_response(response: AssistantResponse, model: LLM) -> None:
    with print_style(Style.PAD):
        print_assistant_heading(model)
        cprint()

        if response.response_text:
            if response.confidence in {Confidence.direct_answer, Confidence.partial_answer}:
                print_text_block(fill_markdown(response.response_text))
            else:
                print_assistance(fill_markdown(response.response_text))

        if response.suggested_commands:
            formatted_commands = "\n\n".join(c.script_str() for c in response.suggested_commands)
            print_small_heading("Suggested commands:")
            print_code_block(formatted_commands)

        if response.python_code:
            print_small_heading("Python code:")
            print_code_block(response.python_code, format="python")

        if response.see_also:
            formatted_see_also = ", ".join(f"`{cmd}`" for cmd in response.see_also)
            print_small_heading("See also:")
            cprint(formatted_see_also, color=COLOR_STATUS, text_wrap=Wrap.WRAP_INDENT)