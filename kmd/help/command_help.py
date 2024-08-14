from typing import Dict, Optional
from kmd.shell_tools.function_inspect import FuncParam
from kmd.text_ui.command_output import format_name_and_description, output, output_help


def output_command_help(
    name: str, description: Optional[str] = None, kw_params: Optional[Dict[str, FuncParam]] = None
):
    command_str = f"the `{name}` command" if name else "this command"

    output()

    if not description:
        output_help(f"Sorry, no help available for {command_str}.")
    else:
        output(format_name_and_description(name, description))

    if kw_params:
        output()
        output_help(f"`{name}` options:")
        for param_name, param in kw_params.items():
            if param.type == bool:
                output(f"    --{param_name}")
            else:
                output(f"    --{param_name}=<value>")

    output()
    output_help(
        "For more information, ask the assistant by typing a question (ending in ?) or check `kmd_help`."
    )
    output()
