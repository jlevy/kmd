from typing import Dict, Optional
from kmd.model.params_model import Param
from kmd.text_formatting.text_formatting import DEFAULT_INDENT
from kmd.text_ui.command_output import Wrap, format_name_and_description, output, output_help


def output_command_help(
    name: str, description: Optional[str] = None, param_info: Optional[Dict[str, Param]] = None
):
    command_str = f"the `{name}` command" if name else "this command"

    output()

    if not description:
        output_help(f"Sorry, no help available for {command_str}.")
    else:
        output(format_name_and_description(name, description))

    if param_info:
        output()
        output_help("Options:")
        for param_name, param in param_info.items():
            desc_suffix = ""
            if param.description:
                desc_suffix = f": {param.description}"
            if param.type == bool:
                output(
                    f"--{param_name}{desc_suffix}",
                    text_wrap=Wrap.HANGING_INDENT,
                    extra_indent=DEFAULT_INDENT,
                )
            else:
                output(
                    f"--{param_name}=<value>{desc_suffix}",
                    text_wrap=Wrap.HANGING_INDENT,
                    extra_indent=DEFAULT_INDENT,
                )

    output()
    output_help(
        "For more information, ask the assistant by typing a question (ending in ?) or check `kmd_help`."
    )
    output()
