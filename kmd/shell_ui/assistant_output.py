from rich.text import Text

from kmd.config.text_styles import COLOR_HINT, EMOJI_ASSISTANT, STYLE_HEADING
from kmd.help.help_page import print_see_also
from kmd.model.assistant_response_model import AssistantResponse
from kmd.model.language_models import LLM
from kmd.shell_ui.rich_markdown_kyrm import KyrmMarkdown
from kmd.shell_ui.shell_output import (
    cprint,
    print_assistance,
    print_code_block,
    print_small_heading,
    print_style,
    Style,
)


def print_assistant_heading(model: LLM) -> None:
    assistant_name = Text(f"{EMOJI_ASSISTANT} Kmd Assistant", style=STYLE_HEADING)
    info = Text(f"({model})", style=COLOR_HINT)
    cprint(assistant_name + " " + info)


def print_assistant_response(response: AssistantResponse, model: LLM) -> None:
    with print_style(Style.PAD):
        print_assistant_heading(model)
        cprint()

        if response.response_text:
            # TODO: indicate confidence level
            print_assistance(KyrmMarkdown(response.response_text))

        if response.suggested_commands:
            formatted_commands = "\n\n".join(c.script_str() for c in response.suggested_commands)
            print_small_heading("Suggested commands:")
            print_code_block(formatted_commands)

        if response.python_code:
            print_small_heading("Python code:")
            print_code_block(response.python_code, format="python")

        if response.see_also:
            print_see_also(response.see_also)
